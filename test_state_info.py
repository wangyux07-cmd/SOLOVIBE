#!/usr/bin/env python3

import sys
import json
import requests
import time
import asyncio

async def test_state_info_fix():
    """测试state_info的has_location修复"""
    
    print("=== 测试State Info修复 ===")
    
    base_url = "http://localhost:8000/api/chat"
    
    # 测试1: 第一次请求 - 心情不好（应该返回has_location: false）
    print("\n1. 测试: 第一次请求 - 心情不好")
    
    request_payload = {
        "message": "心情不好"
    }
    
    try:
        response = requests.post(base_url, json=request_payload)
        if response.status_code == 200:
            data = response.json()
            print(f"响应: {json.dumps(data, ensure_ascii=False, indent=2)}")
            
            state_info = data.get("state_info", {})
            thread_id = data.get("thread_id")
            
            if "has_location" in state_info:
                print(f"✅ has_location字段存在: {state_info['has_location']}")
                print(f"✅ needs_user_input: {state_info.get('needs_user_input', 'missing')}")
                
                if not state_info["has_location"]:
                    print("✅ 正确: 第一次请求应该has_location为false")
                else:
                    print("❌ 错误: 第一次请求has_location应为false")
            else:
                print("❌ 错误: state_info中缺少has_location字段")
        else:
            print(f"❌ HTTP错误: {response.status_code}")
            
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return False
    
    # 等待一下，确保服务响应
    time.sleep(1)
    
    # 测试2: 第二次请求 - 提供地址（应该返回has_location: true）
    print(f"\n2. 测试: 第二次请求 - 提供地址 (使用thread_id: {thread_id})")
    
    request_payload2 = {
        "message": "上海大学站",
        "thread_id": thread_id
    }
    
    try:
        response2 = requests.post(f"{base_url}?thread_id={thread_id}", json=request_payload2)
        if response2.status_code == 200:
            data2 = response2.json()
            print(f"响应: {json.dumps(data2, ensure_ascii=False, indent=2)}")
            
            state_info2 = data2.get("state_info", {})
            thread_id2 = data2.get("thread_id")
            
            if "has_location" in state_info2:
                print(f"✅ has_location字段存在: {state_info2['has_location']}")
                print(f"✅ needs_user_input: {state_info2.get('needs_user_input', 'missing')}")
                print(f"✅ thread_id一致性: {thread_id == thread_id2}")
                
                if state_info2["has_location"]:
                    print("✅ 正确: 提供地址后has_location变为true")
                    return True
                else:
                    print("❌ 错误: 提供地址后has_location应该为true")
                    return False
            else:
                print("❌ 错误: state_info中缺少has_location字段")
                return False
        else:
            print(f"❌ HTTP错误: {response2.status_code}")
            
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return False

if __name__ == "__main__":
    print("启动State Info修复测试...")
    
    # 等待服务启动
    print("等待服务启动...")
    time.sleep(5)
    
    success = asyncio.run(test_state_info_fix())
    
    if success:
        print("\n🎉 State Info修复验证成功!")
    else:
        print("\n❌ State Info修复验证失败!")
        sys.exit(1)