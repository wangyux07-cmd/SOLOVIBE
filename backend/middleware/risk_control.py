import logging
from typing import Dict, Any, List
from datetime import datetime
import json

from data_types import RiskAssessment, ThreadState

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def verify_action_risk(action_data: Dict[str, Any], thread_state: ThreadState) -> RiskAssessment:
    """
    风控验证函数：评估用户请求的风险并决定是否需要人工确认
    
    Args:
        action_data: 用户请求的动作数据
        thread_state: 当前对话线程状态
    
    Returns:
        RiskAssessment: 风险评估结果
    """
    logger.info(f"开始风险评估，动作数据: {json.dumps(action_data, ensure_ascii=False)}")
    
    # 初始化风险评估
    risk_assessment = RiskAssessment(
        is_risky=False,
        risk_level="low",
        message="风险评估完成",
        requires_confirmation=False
    )
    
    try:
        risk_factors = _analyze_risk_factors(action_data, thread_state)
        risk_score = _calculate_risk_score(risk_factors)
        
        # 基于风险分数确定风险等级和是否需要确认
        if risk_score >= 80:
            risk_assessment.is_risky = True
            risk_assessment.risk_level = "high"
            risk_assessment.requires_confirmation = True
            risk_assessment.message = "检测到高风险操作，需要用户确认"
        elif risk_score >= 50:
            risk_assessment.is_risky = True
            risk_assessment.risk_level = "medium"
            risk_assessment.requires_confirmation = True
            risk_assessment.message = "检测到中等风险，建议用户确认"
        elif risk_score >= 20:
            risk_assessment.risk_level = "low"
            risk_assessment.message = "低风险操作，可安全执行"
        else:
            risk_assessment.risk_level = "minimal"
            risk_assessment.message = "极低风险操作"
        
        logger.info(f"风险评估完成 - 等级: {risk_assessment.risk_level}, 需要确认: {risk_assessment.requires_confirmation}")
        
        # 记录风险评估到thread状态
        await _log_risk_assessment(thread_state.thread_id, risk_assessment, risk_factors, risk_score)
        
        return risk_assessment
        
    except Exception as e:
        logger.error(f"风险评估过程中出错: {str(e)}")
        # 出错时保守处理，要求确认
        risk_assessment.is_risky = True
        risk_assessment.risk_level = "unknown"
        risk_assessment.requires_confirmation = True
        risk_assessment.message = "风险评估出错，为安全起见需要确认"
        return risk_assessment


def _analyze_risk_factors(action_data: Dict[str, Any], thread_state: ThreadState) -> Dict[str, Any]:
    """分析具体风险因素"""
    risk_factors = {
        "financial_risk": _assess_financial_risk(action_data),
        "social_risk": _assess_social_risk(action_data),
        "location_risk": _assess_location_risk(action_data),
        "privacy_risk": _assess_privacy_risk(action_data),
        "complexity_risk": _assess_complexity_risk(action_data),
        "user_history_risk": _assess_user_history_risk(thread_state)
    }
    
    logger.debug(f"风险因素分析结果: {risk_factors}")
    return risk_factors


def _assess_financial_risk(action_data: Dict[str, Any]) -> Dict[str, Any]:
    """评估财务风险"""
    risk_info = {"level": "low", "score": 0, "reasons": []}
    
    # 检查是否有费用信息
    if "cost" in action_data:
        cost_str = str(action_data["cost"])
        
        # 提取金额数字
        import re
        cost_numbers = re.findall(r'\d+', cost_str)
        if cost_numbers:
            cost_amount = int(cost_numbers[0])
            
            if cost_amount > 500:
                risk_info["level"] = "high"
                risk_info["score"] = 80
                risk_info["reasons"].append(f"高消费: ¥{cost_amount}")
            elif cost_amount > 100:
                risk_info["level"] = "medium"
                risk_info["score"] = 40
                risk_info["reasons"].append(f"中等消费: ¥{cost_amount}")
            else:
                risk_info["score"] = 10
                risk_info["reasons"].append(f"低消费: ¥{cost_amount}")
    
    return risk_info


def _assess_social_risk(action_data: Dict[str, Any]) -> Dict[str, Any]:
    """评估社交风险"""
    risk_info = {"level": "low", "score": 0, "reasons": []}
    
    # 检查是否涉及社交活动
    action_type = action_data.get("type", "")
    if action_type in ["social_activity", "pk_challenge", "community_interaction"]:
        risk_info["level"] = "medium"
        risk_info["score"] = 30
        risk_info["reasons"].append("涉及陌生人社交互动")
        
        # 检查具体活动类型
        activity_data = action_data.get("data", {})
        if activity_data.get("requires_personal_info", False):
            risk_info["score"] += 20
            risk_info["reasons"].append("需要提供个人信息")
    
    return risk_info


def _assess_location_risk(action_data: Dict[str, Any]) -> Dict[str, Any]:
    """评估位置风险"""
    risk_info = {"level": "low", "score": 0, "reasons": []}
    
    # 检查是否涉及位置信息
    location_fields = ["area", "location", "address", "coordinates"]
    has_location = any(field in action_data for field in location_fields)
    
    if has_location:
        risk_info["score"] = 15
        risk_info["reasons"].append("涉及位置信息共享")
        
        # 检查是否为敏感区域
        area = action_data.get("area", "").lower()
        sensitive_areas = ["偏僻", "夜间", "密闭", "私人"]
        if any(sensitive in area for sensitive in sensitive_areas):
            risk_info["level"] = "medium"
            risk_info["score"] = 45
            risk_info["reasons"].append("位置可能涉及敏感区域")
    
    return risk_info


def _assess_privacy_risk(action_data: Dict[str, Any]) -> Dict[str, Any]:
    """评估隐私风险"""
    risk_info = {"level": "low", "score": 0, "reasons": []}
    
    # 检查是否需要敏感信息
    sensitive_data_fields = ["personal_info", "contact", "payment", "identity"]
    
    for field in sensitive_data_fields:
        if field in str(action_data).lower():
            risk_info["score"] += 25
            risk_info["reasons"].append(f"涉及{field}信息")
    
    if risk_info["score"] > 50:
        risk_info["level"] = "high"
    elif risk_info["score"] > 25:
        risk_info["level"] = "medium"
    
    return risk_info


def _assess_complexity_risk(action_data: Dict[str, Any]) -> Dict[str, Any]:
    """评估操作复杂度风险"""
    risk_info = {"level": "low", "score": 0, "reasons": []}
    
    # 检查操作复杂度
    action_type = action_data.get("type", "")
    
    high_complexity_actions = ["booking", "reservation", "payment", "multi_step"]
    if any(complex_action in action_type for complex_action in high_complexity_actions):
        risk_info["score"] = 35
        risk_info["level"] = "medium"
        risk_info["reasons"].append("涉及复杂操作流程")
    
    # 检查是否需要多个确认步骤
    if action_data.get("requires_multiple_confirmations", False):
        risk_info["score"] += 20
        risk_info["reasons"].append("需要多个确认步骤")
    
    return risk_info


def _assess_user_history_risk(thread_state: ThreadState) -> Dict[str, Any]:
    """基于用户历史评估风险"""
    risk_info = {"level": "low", "score": 0, "reasons": []}
    
    # 检查用户历史记录
    messages = thread_state.messages
    
    if len(messages) < 3:
        # 新用户，稍微保守一些
        risk_info["score"] = 10
        risk_info["reasons"].append("新用户，采用保守策略")
    
    # 检查历史风险记录
    metadata = thread_state.metadata
    if metadata.get("previous_risks", 0) > 0:
        risk_info["score"] = metadata["previous_risks"] * 5
        risk_info["reasons"].append(f"历史风险记录: {metadata['previous_risks']}次")
    
    # 检查是否是首次尝试高风险操作
    if metadata.get("first_high_risk_action", False):
        risk_info["score"] += 15
        risk_info["reasons"].append("首次尝试高风险操作")
    
    if risk_info["score"] > 20:
        risk_info["level"] = "medium"
    
    return risk_info


def _calculate_risk_score(risk_factors: Dict[str, Any]) -> int:
    """计算综合风险分数"""
    total_score = 0
    weights = {
        "financial_risk": 0.3,
        "social_risk": 0.2,
        "location_risk": 0.15,
        "privacy_risk": 0.2,
        "complexity_risk": 0.1,
        "user_history_risk": 0.05
    }
    
    for factor, weight in weights.items():
        if factor in risk_factors:
            total_score += risk_factors[factor]["score"] * weight
    
    return min(int(total_score), 100)  # 限制最高分为100


async def _log_risk_assessment(thread_id: str, assessment: RiskAssessment, 
                              risk_factors: Dict[str, Any], risk_score: int) -> bool:
    """记录风险评估结果"""
    try:
        # 创建风险评估日志
        risk_log = {
            "thread_id": thread_id,
            "timestamp": datetime.utcnow().isoformat(),
            "assessment": {
                "is_risky": assessment.is_risky,
                "risk_level": assessment.risk_level,
                "requires_confirmation": assessment.requires_confirmation,
                "message": assessment.message
            },
            "risk_factors": risk_factors,
            "risk_score": risk_score
        }
        
        logger.info(f"风险评估日志: {json.dumps(risk_log, ensure_ascii=False)}")
        
        # 这里可以将日志保存到数据库
        # await save_risk_log_to_database(risk_log)
        
        return True
        
    except Exception as e:
        logger.error(f"记录风险评估日志时出错: {e}")
        return False


# 便捷函数
async def fast_risk_check(action_data: Dict[str, Any]) -> bool:
    """
    快速风险检查，用于简单场景
    """
    # 简化的风险评估逻辑
    quick_risk_indicators = [
        "payment" in str(action_data).lower(),
        "booking" in str(action_data).lower(),
        "reservation" in str(action_data).lower(),
        "cost" in action_data and _extract_cost_amount(action_data["cost"]) > 200
    ]
    
    return any(quick_risk_indicators)


def _extract_cost_amount(cost_str: str) -> int:
    """从费用字符串中提取金额"""
    import re
    numbers = re.findall(r'\d+', str(cost_str))
    return int(numbers[0]) if numbers else 0
