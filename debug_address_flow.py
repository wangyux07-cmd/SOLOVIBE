#!/usr/bin/env python3
"""
调试地址处理流程
"""

import requests
import json

def debug_address_flow():
    """单步调试地址处理"""
    
    base_url = "http://127.0.0.1:8000/api/chat"
    
    # 步骤1: 纯情感消息
    print("📝 步骤1: 纯情感消息")
    payload1 = {
        "messages": [
            {"role": "user", "content": "和爸妈吵架了，心情不好"}
        ]
    }
    
    response1 = requests.post(base_url, json=payload1, timeout=30)
    result1 = response1.json()
    
    print(f"响应: {result1['response']}")
    thread_id = result1['thread_id']
    
    print(f"\n📍 步骤2: 提供地址 (使用thread_id: {thread_id})")
    payload2 = {
        "messages": [
            {"role": "user", "content": "宝山区"}
        ]
    }
    
    # 使用特定的thread_id
    url_with_thread = f"{base_url}?thread_id={thread_id}"
    response2 = requests.post(url_with_thread, json=payload2, timeout=30)
    result2 = response2.json()
    
    print(f"请求URL: {url_with_thread}")
    print(f"响应: {result2['response']}")
    print(f"线程ID: {result2['thread_id']}")
    print(f"是否相同thread: {result1['thread_id'] == result2['thread_id']}")
    
    if "抱歉" not in result2['response']:
        print(f"\n☕ 步骤3: 后续消息")
        payload3 = {
            "messages": [
                {"role": "user", "content": "我想去咖啡店"}
            ]
        }
        
        url_with_thread3 = f"{base_url}?thread_id={thread_id}"
        response3 = requests.post(url_with_thread3, json=payload3, timeout=30)
        result3 = response3.json()
        
        print(f"响应: {result3['response']}")
        print(f"线程ID: {result3['thread_id']}")
        print(f"是否询问地址: {'哪里' in result3['response'] or '区域' in result3['response']}")

if __name__ == "__main__":
    debug_address_flow()