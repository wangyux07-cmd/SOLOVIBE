#!/usr/bin/env python3
"""
测试Supabase状态保存和加载
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

import asyncio
from services.conversation.manager import ConversationManager
from db.supabase_client import SupabaseClient

async def test_supabase_state():
    """测试Supabase状态管理"""
    
    print("🔍 测试Supabase状态保存和加载")
    
    supabase_client = SupabaseClient()
    conversation_manager = ConversationManager(supabase_client=supabase_client)
    
    test_thread_id = "test-thread-123"
    
    # 测试1: 加载不存在的thread
    print(f"\n=== 测试1: 加载不存在的thread {test_thread_id} ===")
    thread_state1 = await conversation_manager.load_thread_state(test_thread_id)
    print(f"加载的thread_id: {thread_state1.thread_id}")
    print(f"Messages数量: {len(thread_state1.messages)}")
    print(f"Metadata: {thread_state1.metadata}")
    
    # 添加一些数据到metadata
    thread_state1.metadata["address_slot"] = {
        "location": "测试地址",
        "lat": 39.9042,
        "lng": 116.4074,
        "updated_at": "2024-01-01T00:00:00"
    }
    
    # 测试2: 保存状态
    print(f"\n=== 测试2: 保存状态 ===")
    await conversation_manager.save_thread_state(thread_state1)
    print(f"状态已保存")
    
    # 测试3: 重新加载状态
    print(f"\n=== 测试3: 重新加载状态 ===")
    thread_state2 = await conversation_manager.load_thread_state(test_thread_id)
    print(f"重新加载的thread_id: {thread_state2.thread_id}")
    print(f"地址槽位: {thread_state2.metadata.get('address_slot', '未找到')}")
    print(f"地址一致性: {thread_state1.metadata.get('address_slot') == thread_state2.metadata.get('address_slot')}")
    
    print(f"\n=== 总结 ===")
    print(f"✅ Supabase连接: 正常" if thread_state1.metadata.get('address_slot') else "❌ Supabase可能有问题")

if __name__ == "__main__":
    asyncio.run(test_supabase_state())