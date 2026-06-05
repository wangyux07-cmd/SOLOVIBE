#!/usr/bin/env python3
"""
极简测试：只测试地址记忆的核心逻辑
"""

import requests
import json

def test_address_memory():
    """测试地址记忆"""
    
    # 简化测试：只用一个session
    session = requests.Session()
    base_url = "http://127.0.0.1:8000/api/chat"
    
    # 测试用例1: 纯情感消息
    print("🧪 测试地址记忆功能")
    payload1 = {
        "messages": [{"role": "user", "content": "心情不好"}]
    }
    
    r1 = session.post(base_url, json=payload1)
    data1 = r1.json()
    print(f"1. 询问地址: {data1['response'][:50]}")
    
    # 测试用例2: 提供地址
    payload2 = {
        "messages": [{"role": "user", "content": "我在北京"}]
    }
    
    r2 = session.post(base_url, json=payload2)
    data2 = r2.json()
    print(f"2. 记住地址: {data2['response'][:50]}")
    
    # 测试用例3: 继续询问
    payload3 = {
        "messages": [{"role": "user", "content": "推荐咖啡店"}]
    }
    
    r3 = session.post(base_url, json=payload3)
    data3 = r3.json()
    print(f"3. 应该不询问: {data3['response'][:50]}")
    
    # 验证
    asks_location = any("哪里" in d['response'] or "区域" in d['response'] for d in [data1, data2, data3])
    print(f" \n结果: {'✅ 改进有效' if not asks_location or '区域' not in data3['response'] else '❌ 仍有问题'}")

if __name__ == "__main__":
    test_address_memory()