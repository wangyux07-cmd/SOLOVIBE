#!/usr/bin/env python3

"""
显示地调用后端API路径测试
"""
import asyncio
import sys
import os

# 设置路径
project_root = os.path.dirname(os.path.abspath(__file__))
backend_path = os.path.join(project_root, "backend")
sys.path.insert(0, backend_path)

os.chdir(backend_path)

async def simulate_direct_manager():
    """直接调用ConversationManager"""
    
    try:
        from services.conversation.manager import ConversationManager
        
        print("直接调用ConversationManager...")
        
        manager = ConversationManager()
        
        message = "上海大学站"
        thread_id = "3d31e8c1-e81b-40d2-b094-06f11d05dba9"
        
        result, final_thread_id = await manager.process_message(
            message=message,
            thread_id=thread_id
        )
        
        print(f"✅ ConversationManager调用成功:")
        print(f"  result type: {type(result)}")
        print(f"  final_thread_id: {final_thread_id}")
        print(f"  result keys: {result.keys() if result else 'None'}")
        
        return result
        
    except Exception as e:
        print(f"❌ ConversationManager调用失败: {e}")
        import traceback
        traceback.print_exc()
        return None

async def main():
    print("深度-debug API内部调用...")
    
    result2 = await simulate_direct_manager()
    
    if result2:
        print("\n✅ 内部调用成功")
    else:
        print("\n❌ 内部调用失败")

if __name__ == "__main__":
    asyncio.run(main())
