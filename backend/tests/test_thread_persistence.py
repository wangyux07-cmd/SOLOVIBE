import asyncio
import pytest
import sys
import os

# 添加项目路径到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from db.supabase_client import SupabaseClient
from data_types import ThreadState, ThreadStatus
from datetime import datetime


def test_supabase_client_initialization():
    """测试Supabase客户端初始化"""
    client = SupabaseClient()
    assert client is not None
    assert hasattr(client, '_threads_db')
    assert hasattr(client, '_messages_db')
    assert hasattr(client, '_checkpoints_db')
    print("✅ SupabaseClient初始化测试通过")


async def test_thread_creation_and_retrieval():
    """测试线程创建和获取功能"""
    client = SupabaseClient()
    
    # 创建新线程
    thread_id = f"test-thread-{datetime.now().timestamp()}"
    thread_state = await client.get_or_create_thread(thread_id)
    
    assert thread_state.thread_id == thread_id
    assert thread_state.status == ThreadStatus.ACTIVE
    assert len(thread_state.messages) == 0
    
    # 获取已创建的线程
    retrieved_thread = await client.get_thread(thread_id)
    assert retrieved_thread is not None
    assert retrieved_thread.thread_id == thread_id
    assert retrieved_thread.status == ThreadStatus.ACTIVE
    
    print("✅ 线程创建和获取测试通过")


async def test_thread_status_update():
    """测试线程状态更新"""
    client = SupabaseClient()
    
    thread_id = f"test-status-update-{datetime.now().timestamp()}"
    
    # 创建线程
    thread_state = await client.get_or_create_thread(thread_id)
    assert thread_state.status == ThreadStatus.ACTIVE
    
    # 更新状态为等待确认
    success = await client.update_thread_status(thread_id, ThreadStatus.WAITING_CONFIRMATION)
    assert success is True
    
    # 验证状态已更新
    updated_thread = await client.get_thread(thread_id)
    assert updated_thread.status == ThreadStatus.WAITING_CONFIRMATION
    
    # 再次更新为完成状态
    success = await client.update_thread_status(thread_id, ThreadStatus.COMPLETED)
    assert success is True
    
    final_thread = await client.get_thread(thread_id)
    assert final_thread.status == ThreadStatus.COMPLETED
    
    print("✅ 线程状态更新测试通过")


async def test_message_persistence():
    """测试消息持久化功能"""
    client = SupabaseClient()
    
    thread_id = f"test-messages-{datetime.now().timestamp()}"
    
    # 创建线程
    thread_state = await client.get_or_create_thread(thread_id)
    
    # 保存消息
    message1 = "Hello, this is a test message"
    success1 = await client.save_message(thread_id, "user", message1)
    assert success1 is True
    
    message2 = "This is an assistant response"
    success2 = await client.save_message(thread_id, "assistant", message2)
    assert success2 is True
    
    # 获取线程消息
    messages = await client.get_thread_messages(thread_id)
    assert len(messages) == 2
    
    # 验证消息内容
    assert messages[0]["content"] == message1
    assert messages[0]["role"] == "user"
    assert messages[1]["content"] == message2
    assert messages[1]["role"] == "assistant"
    
    print("✅ 消息持久化测试通过")


async def test_checkpoint_persistence():
    """测试检查点持久化功能"""
    from data_types import CheckpointData
    
    client = SupabaseClient()
    
    thread_id = f"test-checkpoint-{datetime.now().timestamp()}"
    checkpoint_id = f"checkpoint-{datetime.now().timestamp()}"
    
    # 创建检查点数据
    checkpoint_data = CheckpointData(
        thread_id=thread_id,
        checkpoint_id=checkpoint_id,
        state={
            "intent": "wander_planning",
            "response_plan": {"suggested_actions": []},
            "last_message": "test message"
        },
        timestamp=datetime.utcnow().isoformat()
    )
    
    # 保存检查点
    success = await client.save_checkpoint(checkpoint_data)
    assert success is True
    
    # 验证检查点已保存（在内存中）
    assert len(client._checkpoints_db) == 1
    saved_checkpoint = client._checkpoints_db[0]
    assert saved_checkpoint["checkpoint_id"] == checkpoint_id
    assert saved_checkpoint["thread_id"] == thread_id
    
    print("✅ 检查点持久化测试通过")


async def test_thread_retrieval_with_messages():
    """测试包含消息的线程检索"""
    client = SupabaseClient()
    
    thread_id = f"test-full-thread-{datetime.now().timestamp()}"
    
    # 创建线程
    thread_state = await client.get_or_create_thread(thread_id)
    
    # 添加消息
    await client.save_message(thread_id, "user", "I want to wander alone")
    await client.save_message(thread_id, "assistant", "I understand, let me help you find a place")
    
    # 获取完整线程状态
    retrieved_thread = await client.get_thread(thread_id)
    assert retrieved_thread is not None
    assert len(retrieved_thread.messages) == 2
    
    # 验证消息结构
    first_message = retrieved_thread.messages[0]
    assert "role" in first_message
    assert "content" in first_message
    assert "timestamp" in first_message
    
    print("✅ 完整线程检索测试通过")


async def test_nonexistent_thread():
    """测试不存在的线程处理"""
    client = SupabaseClient()
    
    # 尝试获取不存在的线程
    thread = await client.get_thread("nonexistent-thread")
    assert thread is None
    
    # 尝试更新不存在的线程状态
    success = await client.update_thread_status("nonexistent-thread", ThreadStatus.COMPLETED)
    assert success is False
    
    print("✅ 不存在线程处理测试通过")


async def test_hitl_interruption_flow():
    """测试HITL中断流程"""
    client = SupabaseClient()
    
    thread_id = f"test-hitl-{datetime.now().timestamp()}"
    
    # 1. 创建新线程
    thread_state = await client.get_or_create_thread(thread_id)
    assert thread_state.status == ThreadStatus.ACTIVE
    
    # 2. 模拟添加用户消息
    await client.save_message(thread_id, "user", "I want to book an expensive restaurant")
    
    # 3. 触发风控中断 - 更新为等待确认状态
    await client.update_thread_status(thread_id, ThreadStatus.WAITING_CONFIRMATION)
    
    # 4. 验证状态
    interrupted_thread = await client.get_thread(thread_id)
    assert interrupted_thread.status == ThreadStatus.WAITING_CONFIRMATION
    
    # 5. 模拟用户确认后恢复
    await client.update_thread_status(thread_id, ThreadStatus.ACTIVE)
    
    # 6. 验证已恢复
    resumed_thread = await client.get_thread(thread_id)
    assert resumed_thread.status == ThreadStatus.ACTIVE
    
    print("✅ HITL中断流程测试通过")


async def run_all_tests():
    """运行所有测试"""
    print("🧪 开始运行SoloVibe线程状态持久化测试...\n")
    
    try:
        # 同步测试
        test_supabase_client_initialization()
        
        # 异步测试
        await test_thread_creation_and_retrieval()
        await test_thread_status_update()
        await test_message_persistence()
        await test_checkpoint_persistence()
        await test_thread_retrieval_with_messages()
        await test_nonexistent_thread()
        await test_hitl_interruption_flow()
        
        print("\n✅ 所有测试通过！")
        print("✅ 线程状态持久化功能验证成功")
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # 运行测试
    success = asyncio.run(run_all_tests())
    
    if success:
        print("\n🎉 SoloVibe线程状态持久化验证完成！")
        sys.exit(0)
    else:
        print("\n💥 验证失败，请检查代码")
        sys.exit(1)
