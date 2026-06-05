import requests
import json

# 测试API
api_url = "http://127.0.0.1:8000/api/chat"

try:
    # 步骤1: 心情不好
    print("步骤1: 心情不好")
    response1 = requests.post(api_url, json={"message": "心情不好想喝酒"})
    print(f"  HTTP {response1.status_code}")
    if response1.status_code == 200:
        result1 = response1.json()
        print(f"  响应: {json.dumps(result1, ensure_ascii=False, indent=4)}")
        thread_id = result1.get('thread_id')
    else:
        print(f"  错误响应: {response1.text}")
        exit(1)
    
    print(f"获取到Thread ID: {thread_id}")
    
    # 步骤2: 提供地址
    print("\n步骤2: 提供地址")
    data2 = {
        "message": "上海大学站",
        "thread_id": thread_id
    }
    response2 = requests.post(api_url, json=data2)
    print(f"  HTTP {response2.status_code}")
    print(f"  请求体: {json.dumps(data2, ensure_ascii=False)}")
    
    if response2.status_code == 200:
        result2 = response2.json()
        print(f"  响应: {json.dumps(result2, ensure_ascii=False, indent=4)}")
        
        # 验证has_location
        state_info = result2.get('state_info', {})
        has_location = state_info.get('has_location')
        print(f"  has_location: {has_location}")
        
        message = result2.get('message', '')
        print(f"  消息长度: {len(message)}")
        
    else:
        print(f"  错误响应: {response2.text}")
        
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()
