#!/usr/bin/env python3
"""
完整业务流测试
"""
import asyncio
import aiohttp
import json
import time
import sys
import os

async def test_conversation_flow():
    """测试:MN心情 -> 地址 -> 商家推荐"""
    
    base_url = "http://127.0.0.1:8000"
    
    async with aiohttp.ClientSession() as session:
        
        # Step 1: 心情不好
        print("\n[步骤1] 发送心情不好消息...")
        async with session.post(f"{base_url}/api/chat", json={
            "message": "心情不好想喝酒"
        }) as resp:
            if resp.status != 200:
                print(f"❌ 步骤1失败: HTTP {resp.status}")
                return False
                
            result1 = await resp.json()
            print(f"✅ 步骤1响应:\n  消息: {result1.get('message', '')}")
            print(f"  Thread ID: {result1.get('thread_id', '')}")
            print(f"  State: {result1.get('state_info', {})}")
            
            thread_id = result1.get('thread_id')
            if not thread_id:
                print("❌ 没有获取到thread_id")
                return False
        
        # 等待一下
        await asyncio.sleep(1)
        
        # Step 2: 提供地址
        print(f"\n[步骤2] 提供地址上海大学站 (thread: {thread_id})...")
        async with session.post(f"{base_url}/api/chat", json={
            "message": "上海大学站",
            "thread_id": thread_id
        }) as resp:
            if resp.status != 200:
                print(f"❌ 步骤2失败: HTTP {resp.status}")
                return False
            
            result2 = await resp.json()
            print(f"✅ 步骤2响应:\n  消息: {result2.get('message', '')}")
            print(f"  Thread ID: {result2.get('thread_id', '')}")
            print(f"  State: {result2.get('state_info', {})}")
            
            # 检查关键点
            state_info = result2.get('state_info', {})
            
            if state_info.get('has_location'):
                print("✅ has_location=True - 修复成功")
            else:
                print("❌ has_location仍为False")
                return False
            
            if "商家" in result2.get('message', '') or "推荐" in result2.get('message', ''):
                print("✅ 包含具体商家推荐 - 修复成功")
            else:
                print("❌ 仍然是通用回复")
                print(f"  完整消息: {result2.get('message', '')}")
                return False
    
    return True

async def main():
    print("开始完整业务流测试...")
    print("🔄 请确保后端服务已启动: python -m uvicorn main:app --host 0.0.0.0 --port 8000")
    
    try:
        success = await test_conversation_flow()
        
        if success:
            print("\n🎉 完整业务流测试成功！所有问题已修复")
            return True
        else:
            print("\n❌ 业务流存在问题")
            return False
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
