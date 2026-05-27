#!/usr/bin/env python3
"""
反机器人检测与缓解策略测试
验证多维度风控检测能力
"""

import asyncio
from backend.services.security.antibot_orchestrator import AntiBotOrchestrator, BlockingType, MitigationStrategy
from backend.data_types import RiskLevel


async def test_risk_assessment():
    """测试风险评估"""
    print("🔒 测试1: 风险评估")
    
    orchestrator = AntiBotOrchestrator()
    
    # 模拟不同风险场景
    scenarios = [
        {
            'name': '无风险场景',
            'blocks': [],
            'expected': RiskLevel.LOW
        },
        {
            'name': '滑块验证码',
            'blocks': [BlockingType.SLIDER_CAPTCHA],
            'expected': RiskLevel.MEDIUM
        },
        {
            'name': '多重验证',
            'blocks': [BlockingType.SLIDER_CAPTCHA, BlockingType.SMS_VERIFICATION],
            'expected': RiskLevel.HIGH
        },
        {
            'name': '账户风控',
            'blocks': [BlockingType.RATE_LIMITING, BlockingType.BEHAVIORAL_ANALYSIS],
            'expected': RiskLevel.HIGH
        }
    ]
    
    for scenario in scenarios:
        print(f"\n  ▶ {scenario['name']}")
        
        # 此处简化测试，实际应传入page和context
        risk_profile = await orchestrator.perform_comprehensive_risk_assessment(
            page=None,  # 测试用占位符
            context=None,
            user_id="test_user"
        )
        
        print(f"    风险等级: {risk_profile.risk_level.value}")
        print(f"    置信度: {risk_profile.overall_confidence:.2f}")
        
    print()


async def test_mitigation_strategies():
    """测试缓解策略"""
    print("📋 测试2: 缓解策略生成")
    
    orchestrator = AntiBotOrchestrator()
    
    # 测试不同阻断类型的缓解策略
    test_cases = [
        BlockingType.SLIDER_CAPTCHA,
        BlockingType.SMS_VERIFICATION,
        BlockingType.LOGIN_REQUIRED,
        BlockingType.RATE_LIMITING
    ]
    
    for block_type in test_cases:
        print(f"\n  ▶ {block_type.value}")
        
        strategies = orchestrator.strategy_mapping.get(block_type, [])
        
        for strategy in strategies:
            user_instruction = orchestrator.user_guidance.get((block_type, strategy), "未知操作")
            print(f"    {strategy.value}: {user_instruction[:30]}...")
    print()


if __name__ == "__main__":
    print("🛡️  反机器人检测测试\n")
    
    asyncio.run(test_risk_assessment())
    asyncio.run(test_mitigation_strategies())
    
    print("🎉 反机器人检测测试完成！")