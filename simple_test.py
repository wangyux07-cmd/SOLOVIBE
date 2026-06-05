#!/usr/bin/env python3
import requests
import json

# 最简单的测试
print("简单API测试")

try:
    r = requests.post("http://127.0.0.1:8000/api/chat", json={
        "message": "你好",
        "thread_id": "test123"
    })
    print(f"状态码: {r.status_code}")
    print(f"响应: {r.text}")
except Exception as e:
    print(f"错误: {e}")