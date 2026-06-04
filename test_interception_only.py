#!/usr/bin/env python3
"""
简化测试，只测试地址拦截机制
"""

import sys
import asyncio
import os

# 添加backend目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.services.agent.langgraph_agent import LangGraphAgent
from backend.data_types import ThreadState, ThreadStatus

def test_address_interception():
    """只测试地址拦截机制"""
    
    # 初始化
    agent = LangGraphAgent()
    thread_state = ThreadState(thread_id="test-interception", status=ThreadStatus.ACTIVE, metadata={})
    
    print("\n" + "="*70)
    print("📍 测试1: 地址拦截 - 分支B温柔询问（无地址）")
    print("="*70)
    
    message_1 = "今天很累，想去安静的地方走走"
    address_result_1 = asyncio.run(agent._intercept_and_store_address(message_1, thread_state))
    
    print(f"输入: {message_1}")
    print(f"地址存在: {address_result_1['address_exists']}")
    if not address_result_1['address_exists']:
        print(f"AI询问: {address_result_1['ai_ask_location_sentence']}")
    
    print("\n" + "="*70)
    print("📍 测试2: 地址拦截 - 分支A（有地址）")
    print("="*70)
    
    message_2 = "我在三里屯soho附近"
    address_result_2 = asyncio.run(agent._intercept_and_store_address(message_2, thread_state))
    
    print(f"输入: {message_2}")
    print(f"地址存在: {address_result_2['address_exists']}")
    print(f"地址值: {address_result_2['address_value']}")
    print(f"Lat: {address_result_2['lat']}")
    print(f"Lng: {address_result_2['lng']}")
    
    print("\n" + "="*70)
    print("📍 测试3: 再次验证地址槽位的更新")
    print("="*70)
    
    print(f"线程metadata中的地址槽位: {thread_state.metadata.get('address_slot', 'N/A')}")
    
    print("\n" + "="*70)
    print("📍 测试4: 测试不同地址（西单）")
    print("="*70)
    
    message_3 = "我在西单大悦城楼下"
    address_result_3 = asyncio.run(agent._intercept_and_store_address(message_3, thread_state))
    
    print(f"输入: {message_3}")
    print(f"地址存在: {address_result_3['address_exists']}")
    print(f"地址值: {address_result_3['address_value']}")
    
    print("\n" + "="*70)
    print("📍 测试5: 最终验证地址槽位的更新")
    print("="*70)
    print(f"线程metadata中的地址槽位: {thread_state.metadata.get('address_slot', 'N/A')}")
    
    # 测试Geo查询功能
    print("\n" + "="*70)
    print("📍 测试6: 简单的Geo坐标查询")
    print("="*70)
    
    coords_1 = asyncio.run(agent.booking_execution_tool.get_location_by_query("三里屯"))
    coords_2 = asyncio.run(agent.booking_execution_tool.get_location_by_query("西单大悦城"))
    
    print(f"三里屯坐标: {coords_1}")
    print(f"西单大悦城坐标: {coords_2}")
    
    # 测试POI查询功能
    print("\n" + "="*70)
    print("📍 测试7: 测试POI查询")
    print("="*70)
    
    pois_1 = asyncio.run(agent.booking_execution_tool.route_query_to_pois("三里屯", results_limit=3))
    pois_2 = asyncio.run(agent.booking_execution_tool.route_query_to_pois("西单", results_limit=2))
    
    print(f"三里屯附近找到 {len(pois_1)} 个POI:")
    for i, poi in enumerate(pois_1[:3]):
        print(f"  {i+1}. {poi.name} ({poi.address}) - 评分: {poi.rating}")
    
    print(f"\n西单附近找到 {len(pois_2)} 个POI:")
    for i, poi in enumerate(pois_2[:2]):
        print(f"  {i+1}. {poi.name} ({poi.address}) - 评分: {poi.rating}")
    
    print("\n" + "="*70)
    print("📍 🎉 地址拦截测试完成")
    print("="*70)

if __name__ == "__main__":
    test_address_interception()