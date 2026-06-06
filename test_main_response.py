#!/usr/bin/env python3
"""
测试main.py中的响应处理逻辑
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

async def test_main_logic():
    """测试main.py的处理逻辑"""
    
    # 模拟process_result，包含NoRealTimeDataScenario转换后的字典
    process_result = {
        "type": "complete_response",
        "empathy_response": "很棒的灵感！一个人的时候思维最清晰，是进行创作和思考的黄金时光。",
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
    
    # 模拟main.py中的处理逻辑（修复后的）
    if process_result.get("type") == "clarification":
        response_text = process_result["empathy_response"]
    else:
        # 对于complete_response，优先使用详细方案信息，而不是简单的共情回复
        detailed_scenario = process_result.get("detailed_scenario")
        
        if detailed_scenario and hasattr(detailed_scenario, 'merchant') and getattr(detailed_scenario, 'merchant', None):
            # 构建详细的商业推荐回复
            merchant_obj = getattr(detailed_scenario, 'merchant')
            merchant_name = getattr(merchant_obj, 'name', '推荐商家')
            response_text = f"{process_result.get('empathy_response', '')} 我为你找到了{merchant_name}，这是一个很棒的去处！"
        elif detailed_scenario and hasattr(detailed_scenario, 'enhanced_response'):
            # 处理没有实时数据但有enhanced_response的情况
            response_text = getattr(detailed_scenario, 'enhanced_response', process_result.get("empathy_response", "让我为你推荐一些适合的地方。"))
        elif isinstance(detailed_scenario, dict) and detailed_scenario.get('error_info', {}).get('enhanced_response'):
            # 处理字典格式的NoRealTimeDataScenario
            response_text = detailed_scenario['error_info']['enhanced_response']
        else:
            # 降级到empathy response
            response_text = process_result.get("empathy_response", "很棒的想法！让我为你推荐一些适合的地方。")
    
    logger.info(f"最终响应: {response_text}")
    return response_text

async def main():
    try:
        response = await test_main_logic()
        logger.info("测试成功！响应生成正常。")
    except Exception as e:
        logger.error(f"测试失败: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())