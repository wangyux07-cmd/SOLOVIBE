#!/usr/bin/env python3
"""
测试新的"情绪+地理位置"双驱动集成逻辑
调用LangGraph Agent的process_message接口，测试地址拦截、Geo注入、plans契约生成
"""

import sys
import asyncio
import logging
from backend.services.agent.langgraph_agent import LangGraphAgent
from backend.services.data.data_types import ThreadState

# 禁用非关键日志
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(name)s - %(message)s')

def test_new_flow():
    """执行流程测试"""
    
    # 初始化
    agent = LangGraphAgent()
    thread_state = ThreadState(thread_id="test-flow", metadata={})
    
    print("\n" + "="*70)
    print("📍 测试1: 地址拦截 - 分支B温柔询问")
    print("="*70)
    
    message_1 = "今天很累，想去安静的地方走走"
    result_1 = asyncio.run(agent.process_message(message_1, thread_state))
    print(f"输入: {message_1}")
    print(f"输出: {result_1}")
    
    print("\n" + "="*70)
    print("📍 测试2: 地址注入 - 用户提供地址")
    print("="*70)
    
    message_2 = "我在三里屯soho附近"
    result_2 = asyncio.run(agent.process_message(message_2, thread_state))
    print(f"输入: {message_2}")
    print(f"输出: {result_2}")
    
    print("\n" + "="*70)
    print("📍 测试3: 分支A完整流程 - Geo注入 + plans契约生成")
    print("="*70)
    
    message_3 = "想去看看附近的治愈地方"
    result_3 = asyncio.run(agent.process_message(message_3, thread_state))
    print(f"输入: {message_3}")
    print(f"输出: {result_3}")
    
    print("\n" + "="*70)
    print("📍 测试4: 再次调用 - 验证Supabase持久化是否工作")
    print("="*70)
    
    message_4 = "还有什么好去处吗"
    result_4 = asyncio.run(agent.process_message(message_4, thread_state))
    print(f"输入: {message_4}")
    print(f"输出: {result_4}")
    
    print("\n" + "="*70)
    print("📍 测试5: 不同地址 - 验证地址槽位更新")
    print("="*70)
    
    message_5 = "我在西单大悦城楼下"
    result_5 = asyncio.run(agent.process_message(message_5, thread_state))
    print(f"输入: {message_5}")
    print(f"输出: {result_5}")
    
    print("\n" + "="*70)
    print("📍 测试6: 验证地址槽位的metadata")
    print("="*70)
    print(f"线程metadata中的地址槽位: {thread_state.metadata.get('address_slot')}")

if __name__ == "__main__":
    test_new_flow()