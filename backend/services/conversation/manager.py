#!/usr/bin/env python3
"""
Conversation Manager - 对话管理服务

职责：
- thread_id 获取/创建
- session 管理
- state 加载/保存  
- message 流程编排（核心入口）
"""

import uuid
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple

from db.supabase_client import SupabaseClient
from services.agent.langgraph_agent import LangGraphAgent
from data_types import ThreadState, ThreadStatus


logger = logging.getLogger(__name__)


class ConversationManager:
    """对话管理器 - 负责完整的对话生命周期管理"""
    
    def __init__(self, supabase_client: Optional[SupabaseClient] = None):
        self.supabase_client = supabase_client
        self.agent = LangGraphAgent(supabase_client=supabase_client)
        
        # 内存缓存，用于快速访问活跃的对话（可选）
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        
    async def get_or_create_thread(self, 
                                 thread_id: Optional[str] = None,
                                 user_id: Optional[str] = None,
                                 client_ip: Optional[str] = None) -> str:
        """获取或创建thread_id
        
        优先级：
        1. 如果提供了thread_id，直接使用
        2. 如果提供了user_id，基于user_id生成稳定的thread_id  
        3. 如果提供了client_ip，基于client_ip生成稳定的thread_id
        4. 否则创建新的随机thread_id
        """
        if thread_id:
            return thread_id
            
        if user_id:
            # 基于用户ID生成稳定的thread_id
            import hashlib
            user_hash = hashlib.md5(f"user_{user_id}".encode()).hexdigest()[:16]
            return f"thread_{user_hash}"
            
        if client_ip:
            # 基于客户端IP生成相对稳定的thread_id（适合同一会话窗口）
            import hashlib
            ip_hash = hashlib.md5(f"ip_{client_ip}".encode()).hexdigest()[:16]
            return f"thread_{ip_hash}"
            
        # 创建新的随机thread_id
        return str(uuid.uuid4())
        
    async def load_thread_state(self, thread_id: str) -> ThreadState:
        """加载线程状态
        
        步骤：
        1. 从持久化存储恢复
        2. 更新内存缓存
        3. 返回ThreadState对象
        """
        thread_state = ThreadState(
            thread_id=thread_id,
            status=ThreadStatus.ACTIVE,
            messages=[],
            metadata={},
            created_at=datetime.now().isoformat()
        )
        
        if self.supabase_client:
            try:
                # 从Supabase加载历史状态
                history_data = await self.supabase_client.load_thread_state(thread_id)
                if history_data:
                    thread_state.metadata.update(history_data)
                    logger.info(f"已从Supabase加载线程{thread_id}状态")
                    
                    # 检查状态的时效性（避免使用过于陈旧的对话状态）
                    updated_at = history_data.get("updated_at")
                    if updated_at:
                        try:
                            update_time = datetime.fromisoformat(updated_at)
                            if datetime.now() - update_time > timedelta(hours=24):
                                logger.info(f"线程{thread_id}状态超过24小时，重置地址信息")
                                # 清除过期的位置信息，但保留其他设置
                                if "address_slot" in thread_state.metadata:
                                    del thread_state.metadata["address_slot"]
                        except:
                            pass
                            
            except Exception as e:
                logger.warning(f"加载线程状态失败，使用新状态: {e}")
                
        return thread_state
        
    async def save_thread_state(self, thread_state: ThreadState) -> None:
        """保存线程状态
        
        步骤：  
        1. 更新metadata中的时间戳
        2. 保存到持久化存储
        3. 更新内存缓存
        """
        # 更新时间戳
        thread_state.metadata["updated_at"] = datetime.now().isoformat()
        thread_state.updated_at = thread_state.metadata["updated_at"]
        
        if self.supabase_client:
            try:
                await self.supabase_client.save_thread_state(
                    thread_state.thread_id, 
                    thread_state.metadata
                )
                logger.info(f"线程{thread_state.thread_id}状态已保存")
            except Exception as e:
                logger.error(f"保存线程状态失败: {e}")
                
    async def process_message(self,
                            message: str,
                            thread_id: str,
                            user_id: Optional[str] = None,
                            client_ip: Optional[str] = None) -> Tuple[Dict[str, Any], str]:
        """处理消息的核心流程 - 主要入口点
        
        正确系统结构：
        Step 1: 获取thread  
        Step 2: 读取state
        Step 3: 解析输入
        Step 4: 更新state  
        Step 5: 基于state决策
        
        返回: (处理结果, thread_id)
        """
        logger.info(f"开始处理消息: '{message}' | thread_id: {thread_id}")
        
        # Step 1: 加载线程状态
        thread_state = await self.load_thread_state(thread_id)
        
        # Step 2: 将消息添加到对话历史
        thread_state.messages.append({
            "role": "user",
            "content": message,
            "timestamp": datetime.now().isoformat()
        })
        
        try:
            # Step 3: 通过Agent处理消息（情感分析 + 决策）
            # Agent只负责AI推理，不处理thread管理
            process_result = await self.agent.process_message(message, thread_state)
            
            # Step 4: 将AI响应添加到对话历史
            if process_result.get("empathy_response"):
                thread_state.messages.append({
                    "role": "model", 
                    "content": process_result["empathy_response"],
                    "timestamp": datetime.now().isoformat()
                })
                
            # Step 5: 保存更新后的状态
            await self.save_thread_state(thread_state)
            
            logger.info(f"消息处理完成 | thread_id: {thread_id}")
            return process_result, thread_id
            
        except Exception as e:
            logger.error(f"消息处理失败: {e}")
            
            # 错误恢复：创建新的线程重试
            if "JSON serializable" in str(e) or "scenario_data" in str(e):
                logger.info(f"检测到序列化错误，尝试新建线程: {thread_id}")
                new_thread_id = str(uuid.uuid4())
                thread_state = ThreadState(
                    thread_id=new_thread_id,
                    status=ThreadStatus.ACTIVE,
                    messages=[],
                    metadata={},
                    created_at=datetime.now().isoformat()
                )
                
                # 将当前消息作为新对话的第一条消息
                thread_state.messages.append({
                    "role": "user",
                    "content": message,
                    "timestamp": datetime.now().isoformat()
                })
                
                process_result = await self.agent.process_message(message, thread_state)
                
                if process_result.get("empathy_response"):
                    thread_state.messages.append({
                        "role": "model",
                        "content": process_result["empathy_response"], 
                        "timestamp": datetime.now().isoformat()
                    })
                    
                await self.save_thread_state(thread_state)
                return process_result, new_thread_id
            
            raise