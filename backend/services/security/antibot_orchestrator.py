"""
反机器人检测与优雅降级编排器
整合多维度风险评估，实现渐进式应对策略
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, List, Tuple
import asyncio
import logging
from datetime import datetime, timedelta
import random

from playwright.async_api import Page, BrowserContext

from ...data_types import RiskLevel


logger = logging.getLogger(__name__)


class BlockingType(Enum):
    """阻断类型枚举"""
    SLIDER_CAPTCHA = "slider_captcha"
    SMS_VERIFICATION = "sms_verification"
    LOGIN_REQUIRED = "login_required"
    PHONE_VERIFICATION = "phone_verification"
    IMAGE_CAPTCHA = "image_captcha"
    BEHAVIORAL_ANALYSIS = "behavioral_analysis"
    RATE_LIMITING = "rate_limiting"
    NONE = "none"


class MitigationStrategy(Enum):
    """缓解策略枚举"""
    CONTINUE_AUTO = "continue_auto"       # 继续自动执行
    REQUEST_USER_HELP = "request_user_help" # 请求用户协助
    SWITCH_ACCOUNT = "switch_account"     # 切换账号
    CHANGE_MERCHANT = "change_merchant"   # 更换商户
    DELAY_RETRY = "delay_retry"           # 延迟重试
    SUSPEND_EXECUTION = "suspend_execution" # 暂停执行


@dataclass
class BlockingEvent:
    """阻断事件数据类"""
    type: BlockingType
    detected_at: str
    confidence: float  # 检测置信度
    selectors: List[str]  # 检测到的选择器
    context_info: Dict[str, Any]  # 上下文信息
    
    def __post_init__(self):
        if not self.detected_at:
            self.detected_at = datetime.now().isoformat()


@dataclass
class RiskProfile:
    """风险画像数据类"""
    risk_level: RiskLevel
    blocking_history: List[BlockingEvent]
    mitigation_strategies: List[MitigationStrategy]
    last_incident: str = ""
    overall_confidence: float = 0.0
    
    def __post_init__(self):
        if not self.last_incident and self.blocking_history:
            self.last_incident = max(event.detected_at for event in self.blocking_history)


@dataclass
class MitigationResult:
    """缓解结果数据类"""
    strategy_used: MitigationStrategy
    success: bool
    applied_at: str
    resolved_after: Optional[str] = None
    notes: str = ""
    metrics: Dict[str, Any] = None
    
    def __post_init__(self):
        if not self.applied_at:
            self.applied_at = datetime.now().isoformat()
        if self.metrics is None:
            self.metrics = {}


class AntiBotOrchestrator:
    """反机器人检测与优雅降级编排器"""
    
    def __init__(self):
        self.user_blocking_history = {}  # 用户阻断历史
        self.session_blocking_count = 0  # 会话阻断计数
        self.last_blocking_time = None  # 上次阻断时间
        
        # 风险阈值配置
        self.risk_thresholds = {
            RiskLevel.LOW: 1,
            RiskLevel.MEDIUM: 3,
            RiskLevel.HIGH: 5,
            RiskLevel.CRITICAL: 10
        }
        
        # 智能选择器库（可扩展）
        self.selector_library = {
            BlockingType.SLIDER_CAPTCHA: [
                '.geetest_slider', '.captcha-slider', '.slider-captcha',
                '[class*="verify"]', '[class*="captcha"]', '[id*="captcha"]',
                '.gt_slider', '.jigsaw', '[class*="slide"]'
            ],
            BlockingType.SMS_VERIFICATION: [
                '[placeholder*="验证码"]', '[placeholder*="验证"]',
                '.send-sms-btn', '.get-code-btn', '.verification-code',
                '[class*="code"]', '[id*="code"]'
            ],
            BlockingType.LOGIN_REQUIRED: [
                '.login-popup', '.wechat-login', '.login-modal',
                '请先登录', '登录后继续', '.login-dialog',
                '[class*="login"]', '#login_btn'
            ],
            BlockingType.PHONE_VERIFICATION: [
                '[placeholder*="手机号"]', '.phone-input',
                '手机验证', '手机号验证', '.tel-input',
                '[name="phone"]', '[name="mobile"]'
            ],
            BlockingType.IMAGE_CAPTCHA: [
                '.captcha-image', '.image-captcha', '.verify-image',
                '[src*="captcha"]', '.captcha', '[id*="verify"]',
                '.identifying_code'
            ],
            BlockingType.BEHAVIORAL_ANALYSIS: [
                # 行为分析特征
                '人机验证', '安全检测', '.behavior-verify',
                '请完成', '.recognition',
                '已开启隐私保护'  # 隐私保护也是一种风控
            ],
            BlockingType.RATE_LIMITING: [
                '操作过于频繁', '访问次数', '时间间隔',
                'try again', 'rate limit', 'too many',
                '请稍后再试', '访问受限'
            ]
        }
        
        # 缓解策略映射
        self.strategy_mapping = {
            BlockingType.SLIDER_CAPTCHA: [
                MitigationStrategy.REQUEST_USER_HELP,
                MitigationStrategy.DELAY_RETRY
            ],
            BlockingType.SMS_VERIFICATION: [
                MitigationStrategy.REQUEST_USER_HELP,
                MitigationStrategy.SWITCH_ACCOUNT
            ],
            BlockingType.LOGIN_REQUIRED: [
                MitigationStrategy.REQUEST_USER_HELP,
                MitigationStrategy.SWITCH_ACCOUNT
            ],
            BlockingType.PHONE_VERIFICATION: [
                MitigationStrategy.REQUEST_USER_HELP,
                MitigationStrategy.CHANGE_MERCHANT
            ],
            BlockingType.IMAGE_CAPTCHA: [
                MitigationStrategy.REQUEST_USER_HELP,
                MitigationStrategy.DELAY_RETRY
            ],
            BlockingType.BEHAVIORAL_ANALYSIS: [
                MitigationStrategy.DELAY_RETRY,
                MitigationStrategy.CHANGE_MERCHANT,
                MitigationStrategy.SUSPEND_EXECUTION
            ],
            BlockingType.RATE_LIMITING: [
                MitigationStrategy.DELAY_RETRY,
                MitigationStrategy.CHANGE_MERCHANT
            ]
        }
        
        # 用户指导文本
        self.user_guidance = {
            (BlockingType.SLIDER_CAPTCHA, MitigationStrategy.REQUEST_USER_HELP): 
                "🤖 页面出现滑块验证，请在截图中拖动滑块完成验证",
            (BlockingType.SMS_VERIFICATION, MitigationStrategy.REQUEST_USER_HELP):
                "📱 需要短信验证码，请查看手机收到的验证码并输入",
            (BlockingType.LOGIN_REQUIRED, MitigationStrategy.REQUEST_USER_HELP):
                "🔐 需要登录授权，请在弹出的登录窗口中完成身份验证（支持微信/手机登录）",
            (BlockingType.PHONE_VERIFICATION, MitigationStrategy.REQUEST_USER_HELP):
                "📞 需要手机号验证，请输入您的手机号码获取验证码",
            (BlockingType.IMAGE_CAPTCHA, MitigationStrategy.REQUEST_USER_HELP):
                "👁️ 出现图形验证码，请识别并输入图中字符",
            (BlockingType.BEHAVIORAL_ANALYSIS, MitigationStrategy.REQUEST_USER_HELP):
                "🛡️ 检测到安全验证，请根据页面提示完成相应操作",
            (BlockingType.RATE_LIMITING, MitigationStrategy.DELAY_RETRY):
                "⏰ 操作过于频繁，系统要求延迟重试，请稍候再试",
            (BlockingType.BEHAVIORAL_ANALYSIS, MitigationStrategy.CHANGE_MERCHANT):
                "🎯 此商户风控较严，已为您推荐替代商户"
        }
    
    async def perform_comprehensive_risk_assessment(self, 
                                                  page: Page, 
                                                  context: BrowserContext,
                                                  user_id: str = "default") -> RiskProfile:
        """
        执行综合风险评估
        """
        detected_blocks = []
        
        # 1. 检测各类阻断
        for block_type, selectors in self.selector_library.items():
            for selector in selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    for element in elements:
                        if await element.is_visible():
                            # 获取元素的文本内容用于判断置信度
                            text_content = await element.text_content() or ""
                            class_attr = await element.get_attribute('class') or ""
                            
                            # 计算置信度
                            confidence = self._calculate_confidence(
                                block_type, selector, text_content, class_attr
                            )
                            
                            detected_blocks.append(BlockingEvent(
                                type=block_type,
                                detected_at=datetime.now().isoformat(),
                                confidence=confidence,
                                selectors=[selector],
                                context_info={
                                    'url': page.url,
                                    'page_title': await page.title(),
                                    'element_text': text_content[:100],
                                    'page_content_sample': await page.content()[:500]
                                }
                            ))
                            
                except Exception as e:
                    logger.debug(f"检测选择器 {selector} 时出错: {e}")
                    continue
        
        # 2. 分析用户历史
        user_history = self._get_user_blocking_history(user_id)
        detected_blocks.extend(user_history[-5:])  # 最近5次阻断记录
        
        # 3. 计算整体风险等级
        risk_level = self._calculate_overall_risk(detected_blocks)
        
        # 4. 生成缓解策略
        mitigation_strategies = self._generate_mitigation_strategies(detected_blocks, risk_level)
        
        # 5. 保存阻断记录
        if detected_blocks:
            await self._record_blocking_events(user_id, detected_blocks)
        
        return RiskProfile(
            risk_level=risk_level,
            blocking_history=detected_blocks,
            mitigation_strategies=mitigation_strategies,
            overall_confidence=self._calculate_overall_confidence(detected_blocks)
        )
    
    async def execute_mitigation_strategy(self,
                                        risk_profile: RiskProfile,
                                        strategy: MitigationStrategy,
                                        page: Page = None,
                                        user_data: Dict[str, Any] = None) -> MitigationResult:
        """
        执行缓解策略
        """
        start_time = datetime.now()
        
        try:
            success = False
            notes = ""
            
            if strategy == MitigationStrategy.REQUEST_USER_HELP:
                success, notes = await self._request_user_assistance(
                    risk_profile.blocking_history, user_data
                )
                
            elif strategy == MitigationStrategy.DELAY_RETRY:
                success, notes = await self._delay_and_retry(
                    page, risk_profile.blocking_history
                )
                
            elif strategy == MitigationStrategy.SWITCH_ACCOUNT:
                success, notes = await self._switch_user_account(user_data)
                
            elif strategy == MitigationStrategy.CHANGE_MERCHANT:
                success, notes = await self._change_target_merchant(user_data)
                
            elif strategy == MitigationStrategy.SUSPEND_EXECUTION:
                success, notes = await self._suspend_current_execution()
                
            resolved_after = (datetime.now() - start_time).total_seconds()
            
            result = MitigationResult(
                strategy_used=strategy,
                success=success,
                applied_at=start_time.isoformat(),
                resolved_after=str(resolved_after),
                notes=notes,
                metrics={
                    'execution_time': resolved_after,
                    'risk_level': risk_profile.risk_level.value,
                    'blocking_count': len(risk_profile.blocking_history)
                }
            )
            
            logger.info(f"缓解策略执行完成: {strategy.value} -> {'成功' if success else '失败'}")
            
            return result
            
        except Exception as e:
            logger.error(f"执行缓解策略失败: {str(e)}")
            
            return MitigationResult(
                strategy_used=strategy,
                success=False,
                applied_at=start_time.isoformat(),
                notes=f"执行失败: {str(e)}",
                metrics={'error': str(e)}
            )
    
    def generate_user_instructions(self, 
                                 risk_profile: RiskProfile, 
                                 strategy: MitigationStrategy) -> str:
        """
        生成用户操作指南
        """
        if not risk_profile.blocking_history:
            return "✅ 未检测到风险，可安全执行"
            
        latest_block = risk_profile.blocking_history[-1]
        
        # 获取基础指导
        base_key = (latest_block.type, strategy)
        instruction = self.user_guidance.get(base_key, "🔍 检测到安全验证，请根据页面提示操作")
        
        # 添加风险等级提示
        risk_labels = {
            RiskLevel.LOW: "🟢 低风险",
            RiskLevel.MEDIUM: "🟡 中风险",
            RiskLevel.HIGH: "🟠 高风险",
            RiskLevel.CRITICAL: "🔴 高风险"
        }
        
        risk_label = risk_labels.get(risk_profile.risk_level, "❓ 未知风险")
        
        # 添加详情说明
        details = f"\n\n【{risk_label}】- {latest_block.type.value} - 置信度: {latest_block.confidence:.1%}"
        
        return instruction + details
    
    def _calculate_confidence(self, 
                            block_type: BlockingType,
                            selector: str,
                            text_content: str,
                            class_attr: str) -> float:
        """
        计算阻断检测置信度
        """
        base_confidence = 0.6  # 基础置信度
        
        # 基于选择器准确性调整
        selector_accuracy = {
            BlockingType.SLIDER_CAPTCHA: 0.9,
            BlockingType.SMS_VERIFICATION: 0.8,
            BlockingType.LOGIN_REQUIRED: 0.85,
            BlockingType.PHONE_VERIFICATION: 0.75,
            BlockingType.IMAGE_CAPTCHA: 0.8,
            BlockingType.BEHAVIORAL_ANALYSIS: 0.7,
            BlockingType.RATE_LIMITING: 0.7
        }
        
        # 基于文本内容调整
        text_keywords = {
            BlockingType.SLIDER_CAPTCHA: ['验证', '拖动', '滑动', 'captcha'],
            BlockingType.SMS_VERIFICATION: ['验证码', '短信', '验证码', 'code'],
            BlockingType.LOGIN_REQUIRED: ['登录', '注册', 'login', 'sign in'],
            BlockingType.PHONE_VERIFICATION: ['手机号', '手机', '电话', 'phone'],
            BlockingType.IMAGE_CAPTCHA: ['图形', '图片', '字符', 'image'],
            BlockingType.BEHAVIORAL_ANALYSIS: ['行为', '安全', '异常', '检测'],
            BlockingType.RATE_LIMITING: ['频繁', '限制', '稍后', '频率']
        }
        
        # 检查关键字匹配
        text_confidence_bonus = 0.0
        if block_type in text_keywords:
            keywords = text_keywords[block_type]
            for keyword in keywords:
                if keyword in text_content or keyword in class_attr.lower():
                    text_confidence_bonus += 0.1
                    
        # 计算最终置信度
        confidence = min(1.0, 
                        base_confidence + 
                        selector_accuracy.get(block_type, 0.7) + 
                        text_confidence_bonus
                        )
        
        return confidence
    
    def _calculate_overall_risk(self, blocking_events: List[BlockingEvent]) -> RiskLevel:
        """
        计算整体风险等级
        """
        if not blocking_events:
            return RiskLevel.LOW
            
        # 基于阻断类型严重程度评分
        severity_scores = {
            BlockingType.SLIDER_CAPTCHA: 2,
            BlockingType.SMS_VERIFICATION: 3,
            BlockingType.LOGIN_REQUIRED: 3,
            BlockingType.PHONE_VERIFICATION: 4,
            BlockingType.IMAGE_CAPTCHA: 2,
            BlockingType.BEHAVIORAL_ANALYSIS: 5,
            BlockingType.RATE_LIMITING: 1
        }
        
        # 计算加权平均分
        total_score = 0.0
        total_weight = 0.0
        
        for event in blocking_events:
            severity = severity_scores.get(event.type, 1)
            weight = event.confidence
            total_score += severity * weight
            total_weight += weight
            
        if total_weight == 0:
            return RiskLevel.LOW
            
        avg_score = total_score / total_weight
        
        # 映射到风险等级
        if avg_score < 2.0:
            return RiskLevel.LOW
        elif avg_score < 3.0:
            return RiskLevel.MEDIUM
        elif avg_score < 4.0:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL
    
    def _generate_mitigation_strategies(self,
                                      blocking_events: List[BlockingEvent],
                                      risk_level: RiskLevel) -> List[MitigationStrategy]:
        """
        生成缓解策略优先级列表
        """
        strategies = set()
        
        # 根据阻断类型添加策略
        for event in blocking_events:
            event_strategies = self.strategy_mapping.get(event.type, [])
            for strategy in event_strategies:
                if event.confidence >= 0.5:  # 只有置信度足够高才添加
                    strategies.add(strategy)
        
        # 根据风险等级调整优先级
        if risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            strategies.add(MitigationStrategy.CHANGE_MERCHANT)
            strategies.add(MitigationStrategy.SUSPEND_EXECUTION)
            
        return list(strategies) if strategies else [MitigationStrategy.REQUEST_USER_HELP]
    
    def _calculate_overall_confidence(self, blocking_events: List[BlockingEvent]) -> float:
        """
        计算整体置信度
        """
        if not blocking_events:
            return 0.0
            
        return sum(event.confidence for event in blocking_events) / len(blocking_events)
    
    def _get_user_blocking_history(self, user_id: str) -> List[BlockingEvent]:
        """获取用户阻断历史"""
        return self.user_blocking_history.get(user_id, [])
    
    async def _record_blocking_events(self, user_id: str, events: List[BlockingEvent]):
        """记录阻断事件"""
        if user_id not in self.user_blocking_history:
            self.user_blocking_history[user_id] = []
            
        self.user_blocking_history[user_id].extend(events)
        
        # 保持最近的50条记录
        self.user_blocking_history[user_id] = self.user_blocking_history[user_id][-50:]
        
        self.session_blocking_count += len(events)
        self.last_blocking_time = datetime.now()
    
    async def _request_user_assistance(self,
                                     blocking_events: List[BlockingEvent],
                                     user_data: Dict[str, Any]) -> Tuple[bool, str]:
        """请求用户协助"""
        latest_event = blocking_events[-1] if blocking_events else None
        
        notes = f"请求用户协助处理 {latest_event.type.value if latest_event else '未知'} 类型阻断"
        
        # 在实际实现中，这里会触发前端交互界面
        # 返回False表示需要人工干预
        return False, notes
    
    async def _delay_and_retry(self,
                             page: Page,
                             blocking_events: List[BlockingEvent]) -> Tuple[bool, str]:
        """延迟并重试"""
        delay_seconds = random.uniform(3, 8)
        
        try:
            await asyncio.sleep(delay_seconds)
            await page.reload()
            await page.wait_for_load_state('networkidle')
            
            # 重新检测是否有阻断
            # simplified check - in practice, re-run assessment
            return True, f"延迟 {delay_seconds:.1f} 秒后刷新页面成功"
            
        except Exception as e:
            return False, f"延迟重试失败: {str(e)}"
    
    async def _switch_user_account(self, user_data: Dict[str, Any]) -> Tuple[bool, str]:
        """切换用户账号"""
        # TODO: 实现账号切换逻辑
        return False, "账号切换功能未实现"
    
    async def _change_target_merchant(self, user_data: Dict[str, Any]) -> Tuple[bool, str]:
        """更换目标商户"""
        # TODO: 实现商户替换逻辑
        return False, "商户更换功能未实现"
    
    async def _suspend_current_execution(self) -> Tuple[bool, str]:
        """暂停当前执行"""
        return True, "执行已暂停，避免进一步触发风控"