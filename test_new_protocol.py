#!/usr/bin/env python3
"""
测试新协议实现
"""

import requests
import json

def test_simplified_protocol():
    """测试简化协议实现"""
    
    print("🔍 测试简化协议实现")
    base_url = "http://127.0.0.1:8001/api/chat"
    
    # 测试1: 初始请求
    print("\n=== 测试1: 初始请求 ===")
    payload1 = {"message": "心情不好"}
    
    r1 = requests.post(base_url, json=payload1)
    data1 = r1.json()
    
    print(f"请求: {payload1}")
    print(f"响应thread_id: {data1['thread_id']}")
    print(f"响应内容: {data1['response']}")
    print(f"State info: {data1.get('state_info', {})}")
    
    thread_id = data1['thread_id']
    
    # 测试2: 发送地址信息
    print(f"\n=== 测试2: 发送地址信息 ===")
    payload2 = {"message": "宝山区", "thread_id": thread_id}
    
    r2 = requests.post(base_url, json=payload2)
    data2 = r2.json()
    
    print(f"请求: {payload2}")
    print(f"响应thread_id: {data2['thread_id']}")
    print(f"响应内容: {data2['response']}")
    print(f"Thread ID一致: {thread_id == data2['thread_id']}")
    print(f"State info: {data2.get('state_info', {})}")
    
    # 测试3: 后续查询（应该不再询问地址）
    print(f"\n=== 测试3: 后续地址查询 ===")
    payload3 = {"message": "附近的咖啡馆", "thread_id": thread_id}
    
    r3 = requests.post(base_url, json=payload3)
    data3 = r3.json()
    
    print(f"请求: {payload3}")
    print(f"响应thread_id: {data3['thread_id']}")
    print(f"响应内容: {data3['response']}")
    print(f"Thread ID一致: {thread_id == data3['thread_id']}")
    print(f"地址询问: {'你在' in data3['response'] and ('区域' in data3['response'] or '哪里' in data3['response'])}")
    
    print(f"\n=== 总结 ===")
    all_threads = [data1['thread_id'], data2['thread_id'], data3['thread_id']]
    unique_threads = len(set(all_threads))
    print(f"总共: {len(all_threads)} requests, {unique_threads} 唯一thread_id")
    print(f"全部相同: {unique_threads == 1}")
    
if __name__ == "__main__":
    test_simplified_protocol()