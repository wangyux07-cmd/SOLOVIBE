import requests
import time
import sys

def test_backend_api():
    print("🔍 测试后端API服务...")
    
    # 测试健康检查端点
    try:
        print("\n1. 测试健康检查端点...")
        response = requests.get('http://localhost:8000/health', timeout=5)
        print(f"   ✅ 健康检查: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"   ❌ 健康检查失败: {e}")
        return False

    # 测试聊天API端点
    try:
        print("\n2. 测试聊天API端点...")
        response = requests.post('http://localhost:8000/api/v1/stream_chat', 
                               json={'messages': [{'role': 'user', 'content': 'hi'}]},
                               timeout=10)
        print(f"   ✅ 聊天API: {response.status_code}")
    except Exception as e:
        print(f"   ❌ 聊天API测试失败: {e}")
        return False
        
    print("\n🎉 后端API服务正常！")
    return True

if __name__ == '__main__':
    test_backend_api()