import os
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import json

from data_types import ThreadState, ThreadStatus, CheckpointData

logger = logging.getLogger(__name__)


class SupabaseClient:
    """
    Supabase客户端封装，处理线程状态持久化（简化模拟版本）
    """
    
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY")
        self.database_url = os.getenv("DATABASE_URL")
        
        # 真实 Supabase 数据库连接
        self.supabase_client = None
        self._is_connected_to_real_db = False
        
        # 内存数据库作为后备存储（当真实数据库不可用时）
        self._threads_db: Dict[str, Dict] = {}
        self._messages_db: List[Dict] = []
        self._checkpoints_db: List[Dict] = []
        
        # 尝试初始化真实数据库连接
        self._init_real_supabase()
        
        if self._is_connected_to_real_db:
            logger.info("SupabaseClient 初始化完成（真实数据库模式）")
        else:
            logger.info("SupabaseClient 初始化完成（后备内存模式）")
    
    def _init_real_supabase(self):
        """初始化真实 Supabase 连接"""
        try:
            if self.supabase_url and self.supabase_key:
                # 动态导入以避免依赖问题
                import supabase
                self.supabase_client = supabase.create_client(
                    self.supabase_url, 
                    self.supabase_key
                )
                self._is_connected_to_real_db = True
                logger.info("成功连接到真实 Supabase 数据库")
            else:
                logger.warning("Supabase 配置缺失，使用内存模式")
        except ImportError:
            logger.warning("Supabase 库未安装，使用内存模式")
        except Exception as e:
            logger.error(f"连接 Supabase 失败: {e}，使用内存模式")
    
    def _get_timestamp(self) -> str:
        """获取当前时间戳"""
        return datetime.utcnow().isoformat()
    
    async def check_connection(self) -> bool:
        """检查数据库连接状态"""
        if self._is_connected_to_real_db and self.supabase_client:
            try:
                # 尝试一个简单的查询来验证连接
                result = self.supabase_client.table('threads').select('count', count='exact').limit(1).execute()
                return True
            except Exception as e:
                logger.error(f"Supabase 连接检查失败: {e}")
                self._is_connected_to_real_db = False
                return False
        return True  # 内存模式始终可用
    
    async def get_thread(self, thread_id: str) -> Optional[ThreadState]:
        """获取特定thread的状态（优先从真实数据库获取）"""
        try:
            # 尝试从真实数据库获取
            if self._is_connected_to_real_db and self.supabase_client:
                result = self.supabase_client.table('threads').select('*').eq('thread_id', thread_id).execute()
                if result.data:
                    thread_data = result.data[0]
                    logger.info(f"从真实数据库获取 thread {thread_id}")
                    return ThreadState(
                        thread_id=thread_data["thread_id"],
                        status=ThreadStatus(thread_data["status"]),
                        messages=thread_data.get("messages", []),
                        metadata=thread_data.get("metadata", {}),
                        created_at=thread_data.get("created_at"),
                        updated_at=thread_data.get("updated_at")
                    )
        except Exception as e:
            logger.error(f"从真实数据库获取 thread {thread_id} 失败: {e}")
            self._is_connected_to_real_db = False
        
        # 回退到内存数据库
        if thread_id in self._threads_db:
            thread_data = self._threads_db[thread_id]
            logger.info(f"从内存数据库获取 thread {thread_id}（回退）")
            return ThreadState(
                thread_id=thread_data["thread_id"],
                status=ThreadStatus(thread_data["status"]),
                messages=thread_data.get("messages", []),
                metadata=thread_data.get("metadata", {}),
                created_at=thread_data.get("created_at"),
                updated_at=thread_data.get("updated_at")
            )
        return None
    
    async def get_or_create_thread(self, thread_id: str) -> ThreadState:
        """获取或创建新的thread"""
        existing_thread = await self.get_thread(thread_id)
        
        if existing_thread:
            return existing_thread
        
        # 创建新thread
        new_thread = ThreadState(
            thread_id=thread_id,
            status=ThreadStatus.ACTIVE,
            messages=[],
            metadata={"created_via": "stream_chat", "version": "0.1.0"},
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat()
        )
        
        # 保存到模拟数据库
        await self.save_thread(new_thread)
        logger.info(f"创建新thread: {thread_id}")
        return new_thread
    
    async def save_thread(self, thread_state: ThreadState) -> bool:
        """保存thread状态"""
        try:
            thread_data = {
                "thread_id": thread_state.thread_id,
                "status": thread_state.status.value,
                "messages": thread_state.messages,
                "metadata": thread_state.metadata,
                "created_at": thread_state.created_at,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            self._threads_db[thread_state.thread_id] = thread_data
            logger.info(f"Thread {thread_state.thread_id} 状态已保存")
            return True
            
        except Exception as e:
            logger.error(f"保存thread {thread_state.thread_id} 时出错: {e}")
            return False
    
    async def update_thread_status(self, thread_id: str, status: ThreadStatus) -> bool:
        """更新thread状态"""
        thread_state = await self.get_thread(thread_id)
        if not thread_state:
            logger.error(f"尝试更新不存在的thread: {thread_id}")
            return False
        
        thread_state.status = status
        thread_state.updated_at = datetime.utcnow().isoformat()
        
        return await self.save_thread(thread_state)
    
    async def update_thread_metadata(self, thread_id: str, metadata_update: Dict[str, Any]) -> bool:
        """更新thread元数据"""
        thread_state = await self.get_thread(thread_id)
        if not thread_state:
            logger.error(f"尝试更新不存在的thread元数据: {thread_id}")
            return False
        
        # 合并新的元数据
        if not thread_state.metadata:
            thread_state.metadata = {}
        
        thread_state.metadata.update(metadata_update)
        thread_state.updated_at = datetime.utcnow().isoformat()
        
        return await self.save_thread(thread_state)
    
    async def save_message(self, thread_id: str, role: str, content: str) -> bool:
        """保存单条消息"""
        try:
            message_data = {
                "id": f"msg-{datetime.utcnow().timestamp()}",
                "thread_id": thread_id,
                "role": role,
                "content": content,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            self._messages_db.append(message_data)
            
            # 更新thread中的消息列表
            thread_state = await self.get_thread(thread_id)
            if thread_state:
                thread_state.messages.append(message_data)
                await self.save_thread(thread_state)
            
            logger.info(f"消息已保存到thread {thread_id}")
            return True
            
        except Exception as e:
            logger.error(f"保存消息到thread {thread_id} 时出错: {e}")
            return False
    
    async def save_checkpoint(self, checkpoint_data: CheckpointData) -> bool:
        """保存LangGraph检查点到数据库（优先真实数据库）"""
        try:
            checkpoint_record = {
                "thread_id": checkpoint_data.thread_id,
                "checkpoint_id": checkpoint_data.checkpoint_id,
                "state": json.dumps(checkpoint_data.state),  # JSON序列化
                "timestamp": checkpoint_data.timestamp
            }
            
            # 优先保存到真实数据库
            if self._is_connected_to_real_db and self.supabase_client:
                try:
                    result = self.supabase_client.table('checkpoints').insert(checkpoint_record).execute()
                    logger.info(f"检查点 {checkpoint_data.checkpoint_id} 已保存到真实数据库")
                    return True
                except Exception as e:
                    logger.error(f"保存检查点到真实数据库失败: {e}")
                    self._is_connected_to_real_db = False
            
            # 回退到内存数据库
            if not self._is_connected_to_real_db:
                checkpoint_record["id"] = f"checkpoint-{self._get_timestamp()}"
                self._checkpoints_db.append(checkpoint_record)
                logger.info(f"检查点 {checkpoint_data.checkpoint_id} 已保存到内存数据库（回退）")
            
            return True
            
        except Exception as e:
            logger.error(f"保存检查点 {checkpoint_data.checkpoint_id} 时出错: {e}")
            return False
    
    async def get_thread_messages(self, thread_id: str) -> List[Dict[str, Any]]:
        """获取thread的所有消息"""
        thread_state = await self.get_thread(thread_id)
        if thread_state:
            return thread_state.messages
        return []
    
    async def get_all_threads(self) -> List[ThreadState]:
        """获取所有threads（用于调试）"""
        threads = []
        for thread_id in self._threads_db:
            thread = await self.get_thread(thread_id)
            if thread:
                threads.append(thread)
        return threads
    
    async def reset_database(self) -> bool:
        """重置模拟数据库（用于测试）"""
        self._threads_db.clear()
        self._messages_db.clear()
        self._checkpoints_db.clear()
        logger.info("模拟数据库已重置")
        return True
