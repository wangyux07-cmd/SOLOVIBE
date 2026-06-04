#!/usr/bin/env python3
"""
测试新的"情绪+地理位置"双驱动集成逻辑
调用LangGraph Agent的process_message接口，测试地址拦截、Geo注入、plans契约生成
"""

import sys
import asyncio
import os

# 添加backend目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.services.agent.langgraph_agent import LangGraphAgent
from backend.data_types import ThreadState, ThreadStatus

def test_new_flow():
    """执行流程测试"""
    
    # 初始化
    agent = LangGraphAgent()
    thread_state = ThreadState(thread_id="test-flow", status=ThreadStatus.ACTIVE, metadata={})
    
    print("\n" + "="*70)
    print("📍 测试1: 地址拦截 - 分支B温柔询问")
    print("="*70)
    
    message_1 = "今天很累，想去安静的地方走走"
    result_1 = asyncio.run(agent.process_message(message_1, thread_state))
    print(f"输入: {message_1}")
    print(f"类型: {result_1.get('type', 'unknown')}")
    if result_1.get('type') == 'clarification':
        print(f"AI询问: {result_1.get('empathy_response', 'N/A')}")
    else:
        print(f"详细结果: {result_1}")
    
    print("\n" + "="*70)
    print("📍 测试2: 地址注入 - 用户提供地址")
    print("="*70)
    
    message_2 = "我在三里屯soho附近"
    result_2 = asyncio.run(agent.process_message(message_2, thread_state))
    print(f"输入: {message_2}")
    print(f"类型: {result_2.get('type', 'unknown')}")
    if result_2.get('type') == 'complete_response':
        plan_count = len(result_2.get('detailed_scenario', {}).get('plans', [])) if result_2.get('detailed_scenario') else 0
        print(f"地址识别成功！找到{plan_count}个推荐去处")
    else:
        print(f"详细结果: {result_2}")
    
    print("\n" + "="*70)
    print("📍 测试3: 验证地址槽位的metadata")
    print("="*70)
    print(f"线程metadata中的地址槽位: {thread_state.metadata.get('address_slot', 'N/A')}")
    
    print("\n" + "="*70)
    print("📍 测试4: 不同地址 - 验证地址槽位更新")
    print("="*70)
    
    message_5 = "我在西单大悦城楼下"
    result_5 = asyncio.run(agent.process_message(message_5, thread_state))
    print(f"输入: {message_5}")
    print(f"类型: {result_5.get('type', 'unknown')}")
    
    print("\n" + "="*70)
    print("📍 测试5: 最终验证地址槽位的metadata更新")
    print("="*70)
    print(f"线程metadata中的地址槽位: {thread_state.metadata.get('address_slot', 'N/A')}")
    
    print("\n" + "="*70)
    print("📍 🎉 所有测试完成")
    print("="*70)

if __name__ == "__main__":
    test_new_flow()