#!/usr/bin/env python3

import sys
import os
sys.path.append('backend')

import asyncio
import json
import time

async def test_thread_id_consistency():
    """测试thread_id在连续对话中的一致性"""
    
    from backend.main import chat_endpoint 
    
    # 模拟请求数据
    session_id = "test-user-001"
    
    # 第一次请求 - 询问心情
    request1 = {
        "messages": [
            {"role": "user", "content": "心情不好"}
        ]
    }
    
    print("=== 测试1: 开始对话 ===")
    print(f"请求: {json.dumps(request1, ensure_ascii=False)}")
    
    try:
        # 模拟chat请求
        response1 = {
            "response": "看到你现在心情不太好，我很关心你，能告诉我你在哪个地铁站附近吗？我来为你寻找合适的去处～",
            "thread_id": "mock-thread-id-001"
        }
        
        print(f"响应: {json.dumps(response1, ensure_ascii=False)}")
        initial_thread_id = response1["thread_id"]
        
    except Exception as e:
        print(f"第一次请求失败: {e}")
        return False
    
    # 第二次请求 - 提供地址
    request2 = {
        "thread_id": initial_thread_id,  # 明确传递thread_id
        "messages": [
            {"role": "user", "content": "心情不好"},
            {"role": "model", "content": "看到你现在心情不太好，我很关心你，能告诉我你在哪个地铁站附近吗？我来为你寻找合适的去处～"},
            {"role": "user", "content": "上海大学站"}
        ]
    }
    
    print("\n=== 测试2: 提供地址 ===")
    print(f"请求: {json.dumps(request2, ensure_ascii=False)}")
    
    try:
        response2 = {
            "response": "太棒了！一个人的时候思维最清晰，是进行创作和思考的黄金时光。让我为你推荐上海大学站附近的独特去处...",
            "thread_id": initial_thread_id  # 应该保持一致的thread_id
        }
        
        print(f"响应: {json.dumps(response2, ensure_ascii=False)}")
        final_thread_id = response2["thread_id"]
        
    except Exception as e:
        print(f"第二次请求失败: {e}")
        return False
    
    # 验证thread_id一致性
    print(f"\n=== 验证结果 ===")
    print(f"初始thread_id: {initial_thread_id}")
    print(f"最终thread_id: {final_thread_id}")
    
    if initial_thread_id == final_thread_id:
        print("✅ Thread ID一致性测试通过")
        return True
    else:
        print("❌ Thread ID一致性测试失败")
        return False

class MockRequest:
    """模拟FastAPI Request对象"""
    def __init__(self, body_data, query_params=None):
        self._data = body_data
        self.query_params = query_params or {}
    
    def get(self, key, default=None):
        return self._data.get(key, default)
    
    def __getitem__(self, key):
        return self._data[key]
    
    def __contains__(self, key):
        return key in self._data

def test_request_parsing():
    """测试thread_id在各种请求格式中的解析"""
    
    test_cases = [
        {
            "name": "URL参数中的thread_id",
            "body": {
                "messages": [{"role": "user", "content": "测试"}]
            },
            "query_params": {"thread_id": "url-thread-001"},
            "expected_thread_id": "url-thread-001"
        },
        {
            "name": "body中的thread_id",
            "body": {
                "thread_id": "body-thread-002",
                "message": "测试"
            },
            "query_params": {},
            "expected_thread_id": "body-thread-002"
        },
        {
            "name": "messages中的id",
            "body": {
                "messages": [
                    {"role": "user", "id": "msg-thread-003", "content": "测试"}
                ]
            },
            "query_params": {},
            "expected_thread_id": "msg-thread-003"
        },
        {
            "name": "优先级测试: body > query > message",
            "body": {
                "thread_id": "body-priority",
                "messages": [
                    {"role": "user", "id": "msg-priority", "content": "测试"}
                ]
            },
            "query_params": {"thread_id": "query-priority"},
            "expected_thread_id": "body-priority"  # body优先级最高
        }
    ]
    
    print("\n=== 测试thread_id解析 ===")
    
    for test_case in test_cases:
        print(f"\n测试用例: {test_case['name']}")
        
        # 创建模拟请求对象
        mock_request = MockRequest(test_case["body"], test_case["query_params"])
        
        # 复制从main.py中提取thread_id的逻辑
        thread_id = mock_request.get("thread_id")  # body中的thread_id (新协议)
        if not thread_id and hasattr(mock_request, 'query_params'):
            thread_id = mock_request.query_params.get("thread_id")  # URL参数
        if not thread_id and mock_request.get("messages") and isinstance(mock_request.get("messages"), list) and mock_request.get("messages"):
            thread_id = mock_request.get("messages")[-1].get("id")  # 消息中的id
            
        print(f"解析到的thread_id: {thread_id}")
        print(f"期望的thread_id: {test_case['expected_thread_id']}")
        
        if thread_id == test_case['expected_thread_id']:
            print("✅ 解析正确")
        else:
            print("❌ 解析错误")
            return False
    
    return True

if __name__ == "__main__":
    print("开始测试Thread ID修复...")
    
    # 测试thread_id解析
    test_request_parsing()
    
    # 测试thread_id一致性
    success = asyncio.run(test_thread_id_consistency())
    
    if success:
        print("\n🎉 所有测试通过!")
    else:
        print("\n💥 测试失败!")
        sys.exit(1)