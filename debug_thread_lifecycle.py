#!/usr/bin/env python3
"""
详细的Thread ID生命周期追踪
"""

import requests
import json
import time

def debug_thread_lifecycle():
    """详细追踪thread_id的生命周期"""
    
    print("🔍 Thread ID生命周期追踪")
    base_url = "http://127.0.0.1:8000/api/chat"
    
    # 测试：发送第一个请求（无thread_id）
    print("\n=== 请求1: 初始请求 ===")
    payload1 = {
        "messages": [
            {"role": "user", "content": "心情不好"}
        ]
    }
    
    r1 = requests.post(base_url, json=payload1)
    data1 = r1.json()
    
    print(f"请求URL: {base_url}")
    print(f"响应thread_id: {data1['thread_id']}")
    print(f"响应内容: {data1['response'][:50]}")
    
    # 保存第一个thread_id
    first_thread_id = data1['thread_id']
    
    # 测试：使用返回的thread_id发送第二个请求
    print(f"\n=== 请求2: 使用第一个thread_id ===")
    payload2 = {
        "messages": [
            {"role": "user", "content": "宝山区"}
        ]
    }
    
    url2 = f"{base_url}?thread_id={first_thread_id}"
    r2 = requests.post(url2, json=payload2)
    data2 = r2.json()
    
    print(f"请求URL: {url2}")
    print(f"请求thread_id参数: {first_thread_id}")
    print(f"响应thread_id: {data2['thread_id']}")
    print(f"响应内容: {data2['response'][:50]}")
    print(f"Thread ID是否一致: {first_thread_id == data2['thread_id']}")
    
    # 测试：继续使用相同的thread_id
    print(f"\n=== 请求3: 继续使用相同thread_id ===")
    payload3 = {
        "messages": [
            {"role": "user", "content": "附近的咖啡店"}
        ]
    }
    
    url3 = f"{base_url}?thread_id={first_thread_id}"
    r3 = requests.post(url3, json=payload3)
    data3 = r3.json()
    
    print(f"请求URL: {url3}")
    print(f"响应thread_id: {data3['thread_id']}")
    print(f"响应内容: {data3['response'][:50]}")
    print(f"与第一个相同: {first_thread_id == data3['thread_id']}")
    print(f"与第二个相同: {data2['thread_id'] == data3['thread_id']}")
    
    print(f"\n=== 总结 ===")
    thread_ids = [data1['thread_id'], data2['thread_id'], data3['thread_id']]
    unique_threads = len(set(thread_ids))
    print(f"总共生成{len(thread_ids)}个thread，{unique_threads}个唯一ID")
    print(f"所有ID: {thread_ids}")
    
    if unique_threads == 1:
        print("✅ Thread ID保持一致")
    elif unique_threads == 2:
        print("⚠️  部分thread重用")
    else:
        print("❌ Thread ID完全不连续")

if __name__ == "__main__":
    debug_thread_lifecycle()