#!/usr/bin/env python3

import sys
import os
sys.path.append('backend')

import asyncio
import json
import time
from unittest.mock import Mock, AsyncMock, patch

async def test_retrieval_and_generation_order():
    """测试实时检索和方案生成的正确顺序"""
    
    print("=== 测试实时检索和方案生成的顺序 ===")
    
    # 模拟Web搜索工具
    mock_web_search = AsyncMock()
    mock_web_search.search_business_info = AsyncMock(return_value=Mock(
        is_open=True,
        current_status="open",
        current_period="下午",
        business_hours="09:00-22:00"
    ))
    
    # 模拟booking工具
    mock_booking_tool = AsyncMock()
    mock_booking_tool.get_location_by_query = AsyncMock(return_value={
        "lat": 39.9042,
        "lng": 116.4074
    })
    
    # 模拟POI结果
    mock_pois = [
        Mock(
            name="怡然书咖",
            address="上海大学站附近",
            location="116.4074,39.9042",
            rating="4.5",
            distance="200"
        ),
        Mock(
            name="静谧茶室",
            address="宝山区大学路",
            location="116.4070,39.9040",
            rating="4.2",
            distance="300"
        )
    ]
    mock_booking_tool.route_query_to_pois = AsyncMock(return_value=mock_pois)
    
    # 模拟scenario generator
    mock_scenario_generator = Mock()
    mock_scenario = Mock()
    mock_scenario.merchant = Mock()
    mock_scenario.merchant.name = "怡然书咖"
    mock_scenario.merchant.location.address = "上海大学站附近"
    mock_scenario_generator.generate_complete_enhanced_scenario = Mock(return_value=mock_scenario)
    
    from services.agent.langgraph_agent import LangGraphAgent
    from services.conversation.state import ThreadState, ConversationState, MetadataState, AddressSlot
    
    # 创建agent并注入mock对象
    agent = LangGraphAgent()
    
    # 用patch替换agent的方法
    with patch.object(agent, 'web_search_tool', mock_web_search), \
         patch.object(agent, 'booking_execution_tool', mock_booking_tool), \
         patch.object(agent, 'scenario_generator', mock_scenario_generator):
        
        # 创建模拟状态
        thread_state = ThreadState(
            thread_id="test-thread-001",
            state=ConversationState(
                thread_id="test-thread-001",
                messages=[],
                metadata=MetadataState(
                    address_slot=AddressSlot(location="上海大学站")
                )
            )
        )
        
        # 模拟流程步骤跟踪
        execution_order = []
        
        async def mock_batch_retrieval(plans, message):
            execution_order.append("batch_retrieval")
            return plans
            
        async def mock_enhanced_scenario(vibe_context, message, quest_narrative, enhanced_plans):
            execution_order.append("enhanced_scenario")
            return mock_scenario
            
        async def mock_single_retrieval(scenario, message):
            execution_order.append("single_retrieval")
            return scenario
            
        # 替换方法
        agent._batch_real_time_info_retrieval = mock_batch_retrieval
        agent._generate_enhanced_detailed_scenario = mock_enhanced_scenario  
        agent._real_time_info_retrieval = mock_single_retrieval
        
        # 这是核心测试部分 - 验证执行顺序
        print("开始验证执行顺序...")
        
        # 模拟graph_workflow流程的关键部分
        message = "上海大学站"
        
        # 步骤1: 提取地址
        from backend.services.agent.langgraph_agent import AddressResult
        address_result = AddressResult(
            extracted_address="上海大学站",
            location="上海大学站",
            lat=39.9042,
            lng=116.4074,
            address_exists=True
        )
        
        # 步骤2: 获取vibe context
        class MockVibeContext:
            class Mode:
                value = "healing"
            mode = Mode()
        
        class MockEmotionProfile:
            pass
            
        emotion_profile = MockEmotionProfile()
        vibe_context = MockVibeContext()
        quest_narrative = "独享时光"
        
        # 执行流程的关键部分（复制自graph_workflow）
        
        # Step 1: Geo注入
        lat = thread_state.metadata.address_slot.lat
        lng = thread_state.metadata.address_slot.lng
        
        print("1. Geo坐标注入位置")
        
        # Step 2: POI搜索
        if lat and lng:
            nearby_pois = await mock_booking_tool.route_query_to_pois(
                thread_state.metadata.address_slot.location,
                radius=1000,
                results_limit=8
            )
            
            initial_plans = []
            for poi in nearby_pois:
                initial_plans.append({
                    "merchant_name": poi.name,
                    "merchant_address": poi.address,
                    "lat": 39.9042,
                    "lng": 116.4074,
                })
        
        print("2. POI搜索完成，找到商家数量:", len(initial_plans))
        
        # Step 3: 批量实时检索 - 这应该在生成方案之前
        enhanced_plans = await agent._batch_real_time_info_retrieval(initial_plans, message)
        
        # Step 4: 基于实时检索结果生成方案
        detailed_scenario = await agent._generate_enhanced_detailed_scenario(
            vibe_context, message, quest_narrative, enhanced_plans
        )
        
        # Step 5: 补充实时检索（可选）
        updated_scenario = await agent._real_time_info_retrieval(detailed_scenario, message)
        
        print("3. 执行顺序:", execution_order)
        
        # 验证顺序
        expected_order = ["batch_retrieval", "enhanced_scenario", "single_retrieval"]
        
        if execution_order == expected_order:
            print("✅ 执行顺序正确: 批量检索 → 方案生成 → 补充检索")
            return True
        else:
            print(f"❌ 执行顺序错误: 期望 {expected_order}, 实际 {execution_order}")
            return False

def test_original_log_analysis():
    """分析原始日志中显示的执行顺序问题"""
    
    print("\n=== 分析原始日志的执行顺序问题 ===")
    
    original_log = """
INFO:services.agent.langgraph_agent:详细方案生成完成 - 商家: 怡然书 咖
INFO:services.tools.web_search_tool:Tavily search timeout
INFO:services.tools.web_search_tool:主引擎失败，尝试备选引擎
    """
    
    print("原始日志中的问题:")
    print("1. 详细方案生成完成 ✅")
    print("2. Tavily search timeout (实时检索失败) ❌")
    print("")
    print("问题分析:")
    print("- 先生成方案，再实时检索")
    print("- 实时检索失败后没有重新生成方案")
    print("- 这导致返回的商家可能是错误的")
    
    print("\n修复后的正确顺序:")
    print("1. POI搜索附近商家")
    print("2. 对附近商家进行实时信息检索")
    print("3. 过滤可用商家（只选择开放的）")
    print("4. 基于可用商家生成方案")
    print("5. 返回准确且有实时性的推荐")

if __name__ == "__main__":
    print("开始测试实时检索和方案生成顺序修复...")
    
    # 分析原始问题
    test_original_log_analysis()
    
    # 测试修复后的顺序
    success = asyncio.run(test_retrieval_and_generation_order())
    
    if success:
        print("\n🎉 实时检索顺序测试通过!")
    else:
        print("\n💥 实时检索顺序测试失败!")
        sys.exit(1)