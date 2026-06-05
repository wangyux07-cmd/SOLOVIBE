#!/usr/bin/env python3
"""
调试API调用，获取详细的错误信息
"""

import requests
import json
import traceback

def debug_api():
    """获取API调用的详细错误信息"""
    
    print("🔍 调试API调用...")
    
    url = "http://127.0.0.1:8000/api/chat"
    payload = {
        "messages": [
            {"role": "user", "content": "测试消息"}
        ]
    }
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
        else:
            print(f"错误响应: {response.text}")
            
    except Exception as e:
        print(f"请求异常: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    debug_api()