#!/usr/bin/env python3
"""
测试SSE处理逻辑
"""
import sys
import os
import asyncio
import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add backend to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

async def test_sse_logic():
    """测试SSE处理逻辑"""
    
    # 模拟process_result，包含NoRealTimeDataScenario转换后的字典
    process_result = {
        "type": "complete_response",
        "empathy_response": "感觉到你今天的能量很棒！想要深度探索的感觉，我很欣赏这种主动的精神🌟",
        "quest": {"title": "测试任务"},
        "detailed_scenario": {
            'scenario_id': 'no_real_time_scenario', 
            'title': '实时数据获取失败 - 上海市宝山区锦秋路', 
            'error_info': {
                'type': 'no_real_time_data', 
                'user_location': '上海市宝山区锦秋路', 
                'failure_reason': '实时搜索失败或无可用商家', 
                'enhanced_response': '很抱歉，我在获取上海市宝山区锦秋路附近的实时商家信息时遇到了技术问题。让我为您提供一些通用的建议...'
            }, 
            'data_source': 'error_fallback', 
            'generated_at': '2026-06-06T15:59:02.547330'
        },
        "copresence": {},
        "requires_confirmation": False,
        "address_status": {
            "has_location": True,
            "location": "上海市宝山区锦秋路"
        }
    }
    
    emotion_context = {"pressure_level": 5, "energy_level": 5}
    
    # 模拟SSE处理逻辑（修复后的版本）
    if process_result.get("type") == "clarification":
        # 发送empathy事件
        empathy_text = process_result.get("empathy_response", "亲爱的，你在哪里呢？我帮你看看附近有什么好去处～")
        print(f"SSE EVENT: empathy - {empathy_text}")
        complete_response = empathy_text
        
        # 检查是否包含地址询问意图
        if "地址查询" in process_result.get("tags", []) or "location" in empathy_text or "地铁" in empathy_text or "区域" in empathy_text:
            print(f"SSE EVENT: location_request - {empathy_text}")
    else:
        # 走新流程：从 LangGraph 里拿到详细场景、再让 DeepSeek 润色输出
        detailed_scenario = process_result.get("detailed_scenario")
        
        if detailed_scenario and hasattr(detailed_scenario, "enhanced_response"):
            # 即使有详细方案，也让 LLM 润色后再流式输出
            enhanced_text = getattr(detailed_scenario, "enhanced_response", None)
            print(f"处理对象格式的detailed_scenario: {enhanced_text}")
            final_text = enhanced_text  # 模拟LLM润色后的结果
            print(f"SSE EVENT: empathy - {final_text}")
            
        elif isinstance(detailed_scenario, dict) and detailed_scenario.get('error_info', {}).get('enhanced_response'):
            # 处理字典格式的NoRealTimeDataScenario
            enhanced_text = detailed_scenario['error_info']['enhanced_response']
            print(f"处理字典格式的detailed_scenario: {enhanced_text}")
            final_text = enhanced_text  # 模拟LLM润色后的结果
            print(f"SSE EVENT: empathy - {final_text}")
        
        else:
            # 没有详细方案，回退到发送empathy_response
            if "empathy_response" in process_result:
                empathy_text = process_result["empathy_response"]
                print(f"SSE EVENT: empathy - {empathy_text}")
                complete_response = empathy_text
        
        # 检查是否有店家信息需要推荐
        if detailed_scenario and hasattr(detailed_scenario, "merchant"):
            merchant = getattr(detailed_scenario, "merchant", None)
            if merchant:
                recommendation_data = {
                    'name': merchant.name if hasattr(merchant, 'name') else str(merchant), 
                    'address': merchant.location.address if hasattr(merchant, 'location') else '',
                    'description': final_text[:100] if 'final_text' in locals() else ''
                }
                print(f"SSE EVENT: business_recommendation - {recommendation_data}")
    
    return complete_response if 'complete_response' in locals() else final_text if 'final_text' in locals() else "默认回复"

async def main():
    try:
        response = await test_sse_logic()
        logger.info(f"最终响应: {response}")
    except Exception as e:
        logger.error(f"测试失败: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())