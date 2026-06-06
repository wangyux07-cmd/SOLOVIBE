#!/usr/bin/env python3
"""
🎯 ReAct Flow 测试脚本

测试LangGraph Agent的ReAct架构是否能够正确处理复合需求
"""

import asyncio
import json
import logging
from dataclasses import asdict
from datetime import datetime
import uuid

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 导入核心组件
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/backend')

from backend.services.agent.langgraph_agent import LangGraphAgent
from backend.services.conversation.manager import ConversationManager
from backend.data_types import ThreadState, ThreadStatus  # 导入数据类


class TestReactFlow:
    """ReAct流程测试类"""
    
    def __init__(self):
        self.conversation_manager = ConversationManager()
        self.agent = LangGraphAgent(supabase_client=None)  # 测试时不使用supabase
    
    async def test_emotional_location_query(self):
        """测试情感+位置查询的复合需求"""
        print("\n" + "="*80)
        print("🎯 测试1: 情感+位置查询复合需求")
        print("="*80)
        
        # 创建新线程
        thread_id = str(uuid.uuid4())
        thread_state = ThreadState(
            thread_id=thread_id,
            status=ThreadStatus.ACTIVE,
            created_at=datetime.now().isoformat()
        )  # 创建ThreadState对象
        
        # 用户消息：同时包含情感表达和位置查询
        message = "我不开心，上海火车站附近有好玩的吗"
        print(f"用户消息: {message}")
        
        # 处理消息
        result = await self.agent.process_message(message, thread_state)
        
        print(f"\nReAct分析结果:")
        print(f"- 需求类型: {result.get('requirement_type', '未知')}")
        print(f"- 情感内容: {result.get('has_emotional_content', False)}")
        print(f"- 位置查询: {result.get('has_location_query', False)}")
        
        # 地址处理结果已经在process_message中更新到thread_state
        address_slot = thread_state.metadata.get('address_slot', {})
        
        print(f"\n地址处理:")
        print(f"- 地址槽位: {address_slot}")
        print(f"- 是否获取到地址: {bool(address_slot.get('location'))}")
        
        return result
    
    async def test_pure_emotional_query(self):
        """测试纯情感表达"""
        print("\n" + "="*80)
        print("🎯 测试2: 纯情感表达")
        print("="*80)
        
        thread_id = str(uuid.uuid4())
        thread_state = ThreadState(
            thread_id=thread_id,
            status=ThreadStatus.ACTIVE,
            created_at=datetime.now().isoformat()
        )
        message = "今天心情很糟糕，感觉很累"
        print(f"用户消息: {message}")
        
        result = await self.agent.process_message(message, thread_state)
        
        print(f"\nReAct分析结果:")
        print(f"- 需求类型: {result.get('requirement_type', '未知')}")
        print(f"- 是否需要位置服务: {result.get('needs_location', False)}")
        
        # 检查是否触发了情感关怀询问
        if result.get('type') == 'emotional_care':
            print(f"- ✅ 情感关怀询问: {result.get('empathy_response', '')}")
        
        return result
    
    async def test_pure_functional_query(self):
        """测试纯功能性需求"""
        print("\n" + "="*80)
        print("🎯 测试3: 纯功能性需求")
        print("="*80)
        
        thread_id = str(uuid.uuid4())
        thread_state = ThreadState(
            thread_id=thread_id,
            status=ThreadStatus.ACTIVE,
            created_at=datetime.now().isoformat()
        )
        message = "王府井附近有电影院吗"
        print(f"用户消息: {message}")
        
        result = await self.agent.process_message(message, thread_state)
        
        print(f"\nReAct分析结果:")
        print(f"- 需求类型: {result.get('requirement_type', '未知')}")
        print(f"- 是否检测到明确地点: {result.get('found_explicit_location', '无')}")
        
        return result
    
    async def test_location_negation(self):
        """测试地点否定表达"""
        print("\n" + "="*80)
        print("🎯 测试4: 地点否定表达")
        print("="*80)
        
        thread_id = str(uuid.uuid4())
        thread_state = ThreadState(
            thread_id=thread_id,
            status=ThreadStatus.ACTIVE,
            created_at=datetime.now().isoformat()
        )
        message = "我不想在上海火车站附近，换个地方吧"
        print(f"用户消息: {message}")
        
        result = await self.agent.process_message(message, thread_state)
        
        print(f"\nReAct分析结果:")
        print(f"- 需求类型: {result.get('requirement_type', '未知')}")
        print(f"- 是否检测到地点: {result.get('found_explicit_location', '无')}")
        print(f"- 是否需要位置服务: {result.get('needs_location', False)}")
        
        return result
    
    async def run_all_tests(self):
        """运行所有测试"""
        print("🎯 ReAct Flow 测试开始")
        print("="*80)
        
        await self.test_emotional_location_query()
        await self.test_pure_emotional_query()
        await self.test_pure_functional_query()
        await self.test_location_negation()
        
        print("\n" + "="*80)
        print("🎯 ReAct Flow 测试完成")
        print("="*80)


if __name__ == "__main__":
    async def main():
        """主函数"""
        try:
            # 设置环境变量
            os.environ['AMAP_API_KEY'] = 'test_key'
            os.environ['TAVILY_API_KEY'] = 'test_key'
            os.environ['SERPER_API_KEY'] = 'test_key'
            
            test_runner = TestReactFlow()
            await test_runner.run_all_tests()
            
        except Exception as e:
            logger.error(f"测试运行失败: {e}")
            import traceback
            traceback.print_exc()
    
    asyncio.run(main())