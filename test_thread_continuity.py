#!/usr/bin/env python3
"""
测试线程连续性：验证地址记忆的改进
"""

import asyncio
import time
from backend.services.conversation.manager import ConversationManager
from backend.db.supabase_client import SupabaseClient


async def test_thread_continuity():
    """测试线程连续性和地址记忆"""
    print("🔄 开始测试线程连续性和地址记忆...\n")
    
    # 创建conversation manager
    supabase_client = SupabaseClient()
    conversation_manager = ConversationManager(supabase_client=supabase_client)
    
    # 使用相同的client_ip来获取稳定的thread_id
    client_ip = "127.0.0.1"
    
    try:
        # Step 1: 获取稳定的thread_id
        thread_id = await conversation_manager.get_or_create_thread(
            thread_id=None,
            client_ip=client_ip
        )
        print(f"🎯 获取到稳定thread_id: {thread_id}")
        
        # Step 2: 测试纯情感表达（无地址）
        print("\n📝 发送纯情感消息（无地址）...")
        message1 = "和爸妈吵架了，心情不好"
        result1, thread_id1 = await conversation_manager.process_message(
            message=message1,
            thread_id=thread_id,
            client_ip=client_ip
        )
        print(f"输入: {message1}")
        print(f"输出类型: {result1.get('type', 'normal')}")
        print(f"响应: {result1.get('empathy_response', '')[:100]}...")
        print(f"是否需要澄清: {result1.get('requires_clarification', False)}")
        
        # Step 3: 测试提供地址
        print("\n📍 发送地址信息...")
        message2 = "我在宝山区"
        result2, thread_id2 = await conversation_manager.process_message(
            message=message2,
            thread_id=thread_id1,  # 使用返回的thread_id
            client_ip=client_ip
        )
        print(f"输入: {message2}")
        print(f"输出类型: {result2.get('type', 'normal')}")
        print(f"响应: {result2.get('empathy_response', '')[:100]}...")
        print(f"是否需要澄清: {result2.get('requires_clarification', False)}")
        
        # Step 4: 测试后续消息（不再询问地址）
        print("\n☕ 发送后续消息（应该记住地址）...")
        message3 = "我想去咖啡店"
        result3, thread_id3 = await conversation_manager.process_message(
            message=message3,
            thread_id=thread_id2,  # 继续使用相同的thread_id
            client_ip=client_ip
        )
        print(f"输入: {message3}")
        print(f"输出类型: {result3.get('type', 'normal')}")
        print(f"响应: {result3.get('empathy_response', '')[:100]}...")
        print(f"是否需要澄清: {result3.get('requires_clarification', False)}")
        
        # 验证thread_id是否保持稳定
        print(f"\n🔍 验证结果:")
        print(f"Thread ID 一致性: {thread_id1 == thread_id2 == thread_id3}")
        print(f"地址询问次数: {sum(1 for r in [result1, result2, result3] if r.get('requires_clarification', False))}")
        
        print("\n✅ 测试完成！")
        print("期望结果：只有第一条消息询问地址，后续消息不询问")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_thread_continuity())