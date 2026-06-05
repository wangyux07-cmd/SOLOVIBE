#!/usr/bin/env python3
"""
调试地址流：测试地址提供后是否生成商业推荐
"""

import asyncio
import json
import requests

def simulate_user_flow():
    """模拟完整用户流程"""
    
    print("🧪 测试地址流")
    base_url = "http://127.0.0.1:8000/api/chat"
    
    # Step 1: 初始消息（无地址，应该询问地址）
    payload1 = {
        "message": "想喝酒",
        "thread_id": "test-thread-123"
    }
    
    print(f"\n=== 请求1: 初始消息 ===")
    print(f"消息: {payload1['message']}")
    
    r1 = requests.post(base_url, json=payload1)
    data1 = r1.json()
    
    print(f"响应: {data1['response'][:50]}")
    print(f"地址询问: {'地铁' in data1['response'] or '区域' in data1['response']}")
    print(f"状态: {data1['state_info']}")
    
    # Step 2: 提供地址
    payload2 = {
        "message": "上海大学站",
        "thread_id": "test-thread-123"
    }
    
    print(f"\n=== 请求2: 提供地址 ===")
    print(f"消息: {payload2['message']}")
    
    r2 = requests.post(base_url, json=payload2)
    data2 = r2.json()
    
    print(f"响应: {data2['response'][:200]}")
    print(f"地址询问: {'地铁' in data2['response'] or '区域' in data2['response']}")
    print(f"状态: {data2['state_info']}")
    print(f"是商业推荐: {'推荐' in data2['response'] or '地方' in data2['response']}")
    
    # Step 3: 再问建议（应该生成商业推荐）
    payload3 = {
        "message": "有什么好的去处吗",
        "thread_id": "test-thread-123"
    }
    
    print(f"\n=== 请求3: 询问推荐 ===")
    print(f"消息: {payload3['message']}")
    
    r3 = requests.post(base_url, json=payload3)
    data3 = r3.json()
    
    print(f"响应: {data3['response'][:200]}")
    print(f"地址询问: {'地铁' in data3['response'] or '区域' in data3['response']}")
    print(f"状态: {data3['state_info']}")
    print(f"是商业推荐: {'推荐' in data3['response'] or '地方' in data3['response']}")
    
    print(f"\n=== 地址流问题分析 ===")
    print(f"请求1: 正确询问地址 = {'地铁' in data1['response']}")
    print(f"请求2: 错误行为 = {not data2['state_info']['has_location'] or '推荐' in data2['response']}")
    print(f"请求3: 应该推荐 = {'推荐' in data3['response']}")

if __name__ == "__main__":
    simulate_user_flow()