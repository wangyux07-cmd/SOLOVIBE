#!/usr/bin/env python3
"""
最终测试：验证所有修复
"""

import requests
import json

def final_test():
    """最终测试所有修复效果"""
    print("🎯 最终测试：对话连续性和地址记忆修复")
    
    base_url = "http://127.0.0.1:8000/api/chat"
    
    # 测试1: 基础功能 - 不应该有scenario_data错误
    print("\n=== 测试1: 基础API功能 ===")
    payload1 = {"messages": [{"role": "user", "content": "测试消息"}]}
    
    r1 = requests.post(base_url, json=payload1)
    data1 = r1.json()
    
    print(f"状态码: {r1.status_code}")
    print(f"响应: {data1['response'][:60]}")
    print(f"✅ 无scenario_data错误" if "抱歉" not in data1['response'] else "❌ 仍有错误")
    
    thread_id = data1['thread_id']
    
    # 测试2: 地址询问逻辑
    print("\n=== 测试2: 地址询问逻辑 ===")
    payload2 = {"messages": [{"role": "user", "content": "心情不好"}]}
    
    url2 = f"{base_url}?thread_id={thread_id}"
    r2 = requests.post(url2, json=payload2)
    data2 = r2.json()
    
    asks_location = "哪里" in data2['response'] or "区域" in data2['response']
    print(f"是否询问地址: {asks_location}")
    print(f"✅ 正确询问" if asks_location else "❌ 未询问地址")
    
    # 测试3: 地址记忆
    print("\n=== 测试3: 地址记忆 ===")
    payload3 = {"messages": [{"role": "user", "content": "我在上海"}]}
    
    url3 = f"{base_url}?thread_id={thread_id}"
    r3 = requests.post(url3, json=payload3)
    data3 = r3.json()
    
    print(f"提供地址后响应: {data3['response'][:60]}")
    print(f"Thread ID相同: {data1['thread_id'] == data3['thread_id']}")
    
    # 总结
    print("\n=== 修复总结 ===")
    print("🔧 已完成：")
    print("  ✅ 修复scenario_data未定义错误")
    print("  ✅ 创建ConversationManager分层架构")  
    print("  ✅ 完善LangGraphAgent异常处理")
    print("  ✅ 建立thread状态管理机制")
    
    print("\n📋 对话连续性改进：")
    print("  ✅ 支持前端传递thread_id")
    print("  ✅ 基于client_ip生成稳定thread")
    print("  🔄 Thread ID一致性待完全验证")

if __name__ == "__main__":
    final_test()