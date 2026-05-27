"""
预订安全门禁模块 - 实现预订前的风险控制和HITL确认触发
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
import json

from enum import Enum


logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """风险级别枚举"""
    LOW = "low"      # 低风险，无需确认
    MEDIUM = "medium" # 中风险，需要确认  
    HIGH = "high"    # 高风险，强烈建议确认
    CRITICAL = "critical"  # 极高风险，必须确认


class BookingType(Enum):
    """预订类型枚举"""
    RESTAURANT = "restaurant"
    TRANSPORT = "transport" 
    ENTERTAINMENT = "entertainment"
    HOTEL = "hotel"
    OTHER = "other"


@dataclass
class RiskFactor:
    """风险因子数据类"""
    name: str
    level: RiskLevel
    description: str
    impact: str  # 对用户的影响说明


@dataclass
class RiskAssessment:
    """风险评估结果"""
    overall_level: RiskLevel
    requires_confirmation: bool
    risk_factors: List[RiskFactor]
    risk_score: float  # 0-10分
    recommendation: str
    mitigation_suggestions: List[str]


@dataclass
class BookingRequest:
    """预订请求数据类"""
    booking_type: BookingType
    merchant_name: str
    location: str
    estimated_cost: float
    planned_time: str  # ISO格式时间
    estimated_duration: int  # 分钟
    requires_external_api: bool
    api_provider: Optional[str] = None
    user_preferences: Dict[str, Any] = None
    special_requirements: List[str] = None


class BookingSafetyGate:
    """
    预订安全门禁 - 执行预订前的全面风险评估
    """
    
    def __init__(self):
        self.risk_thresholds = {
            "cost_medium": 80,        # 80元以上中风险
            "cost_high": 200,         # 200元以上高风险
            "duration_medium": 120,   # 2小时以上中风险
            "duration_high": 360,     # 6小时以上高风险
            "external_api": True,     # 任何外部API都增加风险
        }
        
        # 预订类型风险映射
        self.type_risk_base = {
            BookingType.RESTAURANT: 2,      # 基础风险分数
            BookingType.TRANSPORT: 3,
            BookingType.ENTERTAINMENT: 4,
            BookingType.HOTEL: 6,
            BookingType.OTHER: 5,
        }
        
        # 高风险商户列表（不符合条件时增加风险）
        self.high_risk_merchants = set()
        self.sensitive_time_slots = {
            "late_night": (22, 6),    # 深夜时段
            "rush_hour": (7, 9),      # 上下班高峰
            "peak_dining": (11, 13),  # 用餐高峰期
        }
    
    def _calculate_cost_risk(self, cost: float) -> List[RiskFactor]:
        """计算成本风险"""
        risk_factors = []
        
        if cost > self.risk_thresholds["cost_high"]:
            risk_factors.append(RiskFactor(
                name="high_cost",
                level=RiskLevel.HIGH,
                description=f"预估费用{cost}元超过高风险阈值",
                impact="可能造成较大经济负担，建议仔细确认"
            ))
        elif cost > self.risk_thresholds["cost_medium"]:
            risk_factors.append(RiskFactor(
                name="medium_cost",
                level=RiskLevel.MEDIUM,
                description=f"预估费用{cost}元属于中等消费水平",
                impact="费用较高，建议在预算范围内谨慎选择"
            ))
        
        return risk_factors
    
    def _calculate_duration_risk(self, duration: int) -> List[RiskFactor]:
        """计算时长风险"""
        risk_factors = []
        
        if duration > self.risk_thresholds["duration_high"]:
            risk_factors.append(RiskFactor(
                name="extremely_long_duration", 
                level=RiskLevel.HIGH,
                description=f"计划时长{duration}分钟，属于长时间活动",
                impact="长时间活动可能影响其他安排，建议确认时间安排"
            ))
        elif duration > self.risk_thresholds["duration_medium"]:
            risk_factors.append(RiskFactor(
                name="medium_duration",
                level=RiskLevel.MEDIUM,
                description=f"计划时长{duration}分钟，需要较长时间投入",
                impact="建议评估当天时间安排是否合适"
            ))
        
        return risk_factors
    
    def _calculate_external_dependency_risk(self, 
                                          requires_api: bool, 
                                          api_provider: Optional[str] = None) -> List[RiskFactor]:
        """计算外部依赖风险"""
        if not requires_api:
            return []
        
        risk_factors = [RiskFactor(
            name="external_api_dependency",
            level=RiskLevel.MEDIUM,
            description="此预订需要依赖外部服务接口",
            impact="如果外部服务不稳定可能影响预订成功率"
        )]
        
        # 特定提供商的风险
        if api_provider:
            if "premium" in api_provider.lower() or "vip" in api_provider.lower():
                risk_factors.append(RiskFactor(
                    name="premium_service",
                    level=RiskLevel.MEDIUM,
                    description="涉及高级/VIP服务预订",
                    impact="高级服务通常费用较高且条款较严格"
                ))
        
        return risk_factors
    
    def _calculate_time_risk(self, planned_time: str) -> List[RiskFactor]:
        """计算时间风险"""
        risk_factors = []
        
        try:
            booking_dt = datetime.fromisoformat(planned_time.replace('Z', '+00:00'))
            hour = booking_dt.hour
            weekday = booking_dt.weekday()  # 0=周一, 6=周日
            
            # 深夜时段风险
            if self.sensitive_time_slots["late_night"][0] <= hour or hour <= self.sensitive_time_slots["late_night"][1]:
                risk_factors.append(RiskFactor(
                    name="late_night_booking",
                    level=RiskLevel.MEDIUM,
                    description="深夜时段预订",
                    impact="深夜外出安全需要考虑，建议确认交通和安全安排"
                ))
            
            # 高峰期风险
            if hour in range(self.sensitive_time_slots["rush_hour"][0], self.sensitive_time_slots["rush_hour"][1]) or \
               hour in range(self.sensitive_time_slots["peak_dining"][0], self.sensitive_time_slots["peak_dining"][1]):
                risk_factors.append(RiskFactor(
                    name="peak_hour_booking",
                    level=RiskLevel.LOW,
                    description="高峰期预订",
                    impact="高峰期可能等待时间较长，建议留出充足时间"
                ))
            
            # 周末风险（某些活动周末价格更高）
            if weekday >= 5:  # 周六、周日
                risk_factors.append(RiskFactor(
                    name="weekend_booking",
                    level=RiskLevel.LOW,
                    description="周末预订",
                    impact="周末服务费用可能较高，人流量较大"
                ))
                
        except (ValueError, TypeError) as e:
            logger.error(f"时间解析错误: {e}")
            risk_factors.append(RiskFactor(
                name="invalid_time_format", 
                level=RiskLevel.MEDIUM,
                description="时间格式解析异常",
                impact="建议重新确认预订时间格式是否正确"
            ))
        
        return risk_factors
    
    def _calculate_special_requirements_risk(self, 
                                           special_requirements: List[str]) -> List[RiskFactor]:
        """计算特殊要求风险"""
        if not special_requirements:
            return []
        
        risk_factors = []
        sensitive_keywords = ["特殊需求", "紧急", "加急", "定制", "VIP", "预约", "预付费"]
        
        for requirement in special_requirements:
            if any(keyword in requirement for keyword in sensitive_keywords):
                risk_factors.append(RiskFactor(
                    name="special_requirements",
                    level=RiskLevel.MEDIUM,
                    description=f"包含特殊要求: {requirement}",
                    impact="特殊要求可能导致预订条件更加严格或费用增加"
                ))
        
        return risk_factors
    
    def _calculate_comprehensive_risk_score(self, 
                                          booking_request: BookingRequest, 
                                          risk_factors: List[RiskFactor]) -> float:
        """计算综合风险分数"""
        # 基础风险分数
        base_score = self.type_risk_base.get(booking_request.booking_type, 5)
        
        # 根据风险因子调整
        risk_adjustments = {
            RiskLevel.LOW: 1,
            RiskLevel.MEDIUM: 3,
            RiskLevel.HIGH: 5,
            RiskLevel.CRITICAL: 8
        }
        
        additional_score = sum(risk_adjustments.get(factor.level, 0) for factor in risk_factors)
        
        # 应用外部依赖惩罚
        if booking_request.requires_external_api:
            additional_score += 2
        
        total_score = min(10, base_score + additional_score)  # 最高10分
        
        logger.info(f"风险评估计算完成: {booking_request.booking_type.value} - 分数: {total_score}")
        return total_score
    
    def _determine_overall_risk_level(self, risk_score: float) -> RiskLevel:
        """根据分数确定整体风险级别"""
        if risk_score >= 8:
            return RiskLevel.CRITICAL
        elif risk_score >= 6:
            return RiskLevel.HIGH
        elif risk_score >= 4:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _generate_recommendation(self, 
                               overall_level: RiskLevel, 
                               risk_score: float) -> str:
        """生成风险建议"""
        recommendations = {
            RiskLevel.LOW: "风险较低，可以放心预订",
            RiskLevel.MEDIUM: f"中等风险 (分数: {risk_score}/10)，建议仔细确认细节",
            RiskLevel.HIGH: f"高风险 (分数: {risk_score}/10)，强烈建议用户确认",
            RiskLevel.CRITICAL: f"极高风险 (分数: {risk_score}/10)，必须进行用户确认"
        }
        
        return recommendations.get(overall_level, "需要进一步评估")
    
    def _generate_mitigation_suggestions(self, 
                                       risk_factors: List[RiskFactor], 
                                       booking_request: BookingRequest) -> List[str]:
        """生成风险缓解建议"""
        suggestions = []
        
        for factor in risk_factors:
            if factor.name == "high_cost":
                suggestions.append("考虑预订费用较低的替代方案")
                suggestions.append("确认预算范围是否包含此消费")
            
            elif factor.name == "external_api_dependency":
                suggestions.append("确保网络连接稳定")
                suggestions.append("建议提前测试预订系统的可用性")
            
            elif factor.name == "late_night_booking":
                suggestions.append("安排安全的交通方式")
                suggestions.append("告知朋友自己的外出计划")
            
            elif factor.name == "extremely_long_duration":
                suggestions.append("考虑分段进行，避免过度疲劳")
                suggestions.append("确认当天是否有足够的时间安排")
            
            elif factor.name == "peak_hour_booking":
                suggestions.append("提前到达，预留排队时间")
                suggestions.append("考虑选择非高峰期的时间")
        
        # 通用建议
        if booking_request.estimated_cost > 50:
            suggestions.append("确认付款方式可用")
        
        suggestions.append("确认预订详情无误")
        suggestions.append("保存预订确认信息")
        
        return list(set(suggestions))  # 去重
    
    async def assess_booking_risk(self, booking_request: BookingRequest) -> RiskAssessment:
        """
        执行完整的预订风险评估
        """
        logger.info(f"开始风险评估: {booking_request.booking_type.value} - {booking_request.merchant_name}")
        
        all_risk_factors = []
        
        # 各项风险分析
        all_risk_factors.extend(self._calculate_cost_risk(booking_request.estimated_cost))
        all_risk_factors.extend(self._calculate_duration_risk(booking_request.estimated_duration))
        all_risk_factors.extend(self._calculate_time_risk(booking_request.planned_time))
        all_risk_factors.extend(
            self._calculate_external_dependency_risk(
                booking_request.requires_external_api, 
                booking_request.api_provider
            )
        )
        all_risk_factors.extend(
            self._calculate_special_requirements_risk(
                booking_request.special_requirements or []
            )
        )
        
        # 计算综合风险分数
        risk_score = self._calculate_comprehensive_risk_score(booking_request, all_risk_factors)
        
        # 确定整体风险级别
        overall_level = self._determine_overall_risk_level(risk_score)
        
        # 生成建议和缓解措施
        recommendation = self._generate_recommendation(overall_level, risk_score)
        mitigation_suggestions = self._generate_mitigation_suggestions(
            all_risk_factors, booking_request
        )
        
        # 确定是否需要用户确认
        requires_confirmation = overall_level in [RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
        
        logger.info(f"风险评估完成 - 级别: {overall_level.value}, 分数: {risk_score}, 需要确认: {requires_confirmation}")
        
        return RiskAssessment(
            overall_level=overall_level,
            requires_confirmation=requires_confirmation,
            risk_factors=all_risk_factors,
            risk_score=risk_score,
            recommendation=recommendation,
            mitigation_suggestions=mitigation_suggestions
        )
    
    def generate_confirmation_message(self, risk_assessment: RiskAssessment, 
                                    booking_request: BookingRequest) -> Dict[str, Any]:
        """生成用户确认消息"""
        message_data = {
            "type": "booking_confirmation_required",
            "title": "预订确认",
            "message": f"即将为您预订 {booking_request.merchant_name}",
            "risk_level": risk_assessment.overall_level.value,
            "risk_score": risk_assessment.risk_score,
            "requires_confirmation": risk_assessment.requires_confirmation,
            "booking_details": {
                "type": booking_request.booking_type.value,
                "merchant": booking_request.merchant_name,
                "location": booking_request.location,
                "estimated_cost": booking_request.estimated_cost,
                "planned_time": booking_request.planned_time,
                "duration": booking_request.estimated_duration
            },
            "risk_factors": [asdict(factor) for factor in risk_assessment.risk_factors],
            "recommendation": risk_assessment.recommendation,
            "mitigation_suggestions": risk_assessment.mitigation_suggestions,
            "confirmation_options": [
                {
                    "action": "confirm",
                    "label": "确认预订",
                    "style": "primary" if risk_assessment.overall_level != RiskLevel.CRITICAL else "warning"
                },
                {
                    "action": "modify", 
                    "label": "修改预订",
                    "style": "secondary"
                },
                {
                    "action": "cancel",
                    "label": "取消预订", 
                    "style": "danger"
                }
            ]
        }
        
        return message_data
    
    def should_trigger_hitl(self, booking_request: BookingRequest) -> bool:
        """
        快速判断是否应触发HITL中断
        用于在详细的风险评估前的初步筛选
        """
        quick_checks = [
            booking_request.estimated_cost > self.risk_thresholds["cost_high"],
            booking_request.estimated_duration > self.risk_thresholds["duration_high"],
            booking_request.requires_external_api,
            booking_request.booking_type in [BookingType.HOTEL, BookingType.ENTERTAINMENT]
        ]
        
        return any(quick_checks)