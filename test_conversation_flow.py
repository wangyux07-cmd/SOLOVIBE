#!/usr/bin/env python3
"""
测试对话流程连续性 - 模拟前端调用
"""

import requests
import json
import time

def test_conversation_flow():
    """测试对话连续性和地址记忆"""
    
    print("🧪 开始测试对话流程连续性...")
    
    base_url = "http://127.0.0.1:8000/api/chat"
    
    # 模拟前端会话
    current_thread_id = None
    
    # 测试用例1: 纯情感消息（无地址）
    print("\n📝 测试用例1: 纯情感消息")
    payload1 = {
        "messages": [
            {"role": "user", "content": "和爸妈吵架了，心情不好"}
        ]
    }
    
    if current_thread_id:
        url = f"{base_url}?thread_id={current_thread_id}"
    else:
        url = base_url
        
    print(f"请求URL: {url}")
    print(f"发送消息: {payload1['messages'][0]['content']}")
    
    response1 = requests.post(url, json=payload1, timeout=30)
    result1 = response1.json()
    
    print(f"响应: {result1['response'][:100]}...")
    print(f"返回的thread_id: {result1['thread_id']}")
    
    # 保存thread_id用于后续请求
    current_thread_id = result1['thread_id']
    
    time.sleep(1)  # 等待状态保存
    
    # 测试用例2: 提供地址
    print("\n📍 测试用例2: 提供地址信息")
    payload2 = {
        "messages": [
            {"role": "user", "content": "和爸妈吵架了，心情不好"},
            {"role": "model", "content": result1['response']},
            {"role": "user", "content": "宝山区"}
        ]
    }
    
    url = f"{base_url}?thread_id={current_thread_id}"
    print(f"发送消息: 宝山区")
    
    response2 = requests.post(url, json=payload2, timeout=30)
    result2 = response2.json()
    
    print(f"响应: {result2['response'][:100]}...")
    print(f"返回的thread_id: {result2['thread_id']}")
    
    time.sleep(1)
    
    # 测试用例3: 后续消息（应该记住地址，不再询问）
    print("\n☕ 测试用例3: 后续消息（应记住地址）")
    payload3 = {
        "messages": [
            {"role": "user", "content": "和爸妈吵架了，心情不好"},
            {"role": "model", "content": result1['response']},
            {"role": "user", "content": "宝山区"},
            {"role": "model", "content": result2['response']},
            {"role": "user", "content": "我想去咖啡店"}
        ]
    }
    
    url = f"{base_url}?thread_id={current_thread_id}"
    print(f"发送消息: 我想去咖啡店")
    
    response3 = requests.post(url, json=payload3, timeout=30)
    result3 = response3.json()
    
    print(f"响应: {result3['response'][:100]}...")
    print(f"返回的thread_id: {result3['thread_id']}")
    
    # 验证结果
    print("\n🔍 验证结果:")
    print(f"Thread ID 一致性: {len(set([result1['thread_id'], result2['thread_id'], result3['thread_id']])) == 1}")
    
    # 检查是否在第三条消息中还询问地址
    asks_for_location = "哪里" in result3['response'] or "区域" in result3['response'] or "位置" in result3['response']
    print(f"第三条消息是否询问地址: {asks_for_location}")
    print(f"期望结果: False（不应询问地址）")
    
    if not asks_for_location:
        print("✅ 对话连续性修复成功！系统记住了地址信息")
    else:
        print("❌ 还需要进一步优化地址记忆逻辑")

if __name__ == "__main__":
    test_conversation_flow()