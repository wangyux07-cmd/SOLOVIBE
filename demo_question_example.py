#!/usr/bin/env python3

import asyncio
import uuid
import sys
from datetime import datetime

# 添加正确的模块路径
sys.path.append('../')
sys.path.append('./')

from services.agent.langgraph_agent import LangGraphAgent
from services.conversation.manager import ThreadState, ThreadStatus

async def simple_demo():
    """简洁demo: 展示主动关怀询问功能"""
    print("=" * 60)
    print("🌟 LangGraph Agent 情感关怀 demo")
    print("=" * 60)

    agent = LangGraphAgent()
    
    # test
    test_messages = [
        "我好累",
        "今天心情不好",
        "工作压力很大",
        "我感觉很疲惫"
    ]
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n💬 场景 {i}: " + message)
        print("-" * 40)
    
        thread_id = str(uuid.uuid4())
        state = ThreadState(
            thread_id=thread_id,
            status=ThreadStatus.ACTIVE,
            created_at=datetime.now().isoformat()
        )
        
        # 由于_analyze_react_requirements是内部方法，这里用process_message演示
        response = await agent.process_message(message, state)
        
        # 模拟分析结果（实际在process_message内部处理）
        result_info = "emotional" if any(word in message for word in ["累", "疲惫", "心情不好", "压力大"]) else "functional"

        print(f"🧠分析:")
        print(f"  - 需求类型: {result_info}")
        print(f"  - 情感内容: {'✓' if result_info == 'emotional' else '✗'}")
        print(f"  - 需要地址: ✗")
        

        if response.get('type') == 'emotional_care':
            print(f"✨ 关怀:")
            print(f"  {response['empathy_response']}")
        else:
            print(f"💡 方案: {response.get('type', '默认')}")

if __name__ == "__main__":
    asyncio.run(simple_demo())
    print("\n✅ Demo 结束！")