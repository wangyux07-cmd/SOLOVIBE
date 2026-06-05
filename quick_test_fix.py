#!/usr/bin/env python
import requests
import json

api_url = "http://127.0.0.1:8000/api/chat"

print("快速验证传感器修复结果...")

# Step 1 - 模拟心情
print("\n1. 发送心情不好...")
res1 = requests.post(api_url, json={"message": "心情不好想喝酒"}, timeout=10)
print(f"    状态: {res1.status_code}")

if res1.status_code == 200:
    result1 = res1.json()
    print("    ✅ 步骤1成功")
    print(f"    Thread ID: {result1.get('thread_id')}")
    print(f"    State: {result1.get('state_info', {})}")
    
    tid1 = result1.get('thread_id')
    
    if tid1:
        # Step 2 - 提供地址
        print("\n2. 提供地址上海大学站...")
        res2 = requests.post(api_url, json={
            "message": "上海大学站",
            "thread_id": tid1
        }, timeout=10)
        
        print(f"    状态: {res2.status_code}")
        
        if res2.status_code == 200:
            result2 = res2.json()
            
            print(f"    响应内容: {result2}")
            
            # 检查核心修复指标
            state_info = result2.get('state_info', {})
            print(f"\n🔍 重要指标:")
            print(f"    has_location: {state_info.get('has_location', False)}")
            print(f"    message length: {len(result2.get('message', ''))}")
            
            response_text = result2.get('message', '')
            has_business = '商家' in response_text or '推荐' in response_text
            print(f"    contains business: {has_business}")
            
            if state_info.get('has_location') and has_business:
                print("\n🎉 全部修复成功！")
            elif "抱歉" not in response_text:
                print("\n✅ 问题改善：不再显示错误消息")
            else:
                print("\n⚠️  还有问题待解决")
        else:
            print(f"    ❌ 步骤2失败: {res2.status_code} - {res2.text}")
    else:
        print("    ❌ 无Thread ID")
else:
    print(f"    ❌ 步骤1失败: {res1.status_code} - {res1.text}")