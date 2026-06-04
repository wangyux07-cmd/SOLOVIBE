#!/usr/bin/env python3
"""
测试 FastAPI 后端是否正常工作
"""
import requests
import json

# 测试健康检查端点
def test_health():
    try:
        response = requests.get("http://127.0.0.1:8000/health", timeout=5)
        print(f"✅ 健康检查: {response.status_code}")
        print(f"响应: {response.json()}")
        return True
    except Exception as e:
        print(f"❌ 健康检查失败: {e}")
        return False

# 测试聊天接口
def test_chat():
    try:
        data = {
            "messages": [
                {
                    "role": "user",
                    "content": "我好累，想出门走走"
                }
            ]
        }
        
        response = requests.post(
            "http://127.0.0.1:8000/api/chat",
            json=data,
            timeout=30
        )
        
        print(f"✅ 聊天接口: {response.status_code}")
        print(f"响应: {response.json()}")
        return True
    except Exception as e:
        print(f"❌ 聊天接口失败: {e}")
        return False

if __name__ == "__main__":
    print("🔍 开始测试 SoloVibe 后端 API...")
    print("=" * 50)
    
    if test_health():
        print("\n🟢 后端健康检查通过！")
        test_chat()
    else:
        print("\n🔴 后端有问题，请检查 Python 日志！")