import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import json
import re
import random
from dataclasses import dataclass, asdict
from enum import Enum

# 🆕 位置询问库
LOCATION_ASK_SENTENCES = [
    "亲爱的，你在哪个地铁站附近？我帮你看看周边有什么治愈的好去处～",
    "你在哪个区域？我查一下附近有什么安静的地方～",
    "你在哪个区？我为你找找附近的安静角落～",
    "你在哪儿呀？我帮你看看附近有什么好去处～",
    "能告诉我你在哪个区域吗？我帮你查查附近有什么适合一个人的小确幸～",
    "你在哪儿？我为你找找附近适合独处的地方～",
    "你现在在哪个地铁站附近？我帮你看看有什么方法可以舒缓一下～",
    "你在哪儿呀？我帮你瞅瞅附近有什么安静的地方可以待会儿～",
]

from data_types import ThreadState, CheckpointData
from services.data.scenario_generator import EnhancedScenarioGenerator
from services.tools.web_search_tool import WebSearchTool, SearchQuery, BusinessInfo
from services.tools.booking_safety_gate import BookingSafetyGate, BookingRequest, BookingType, RiskAssessment
from services.tools.booking_execution_tool import (
    PlaywrightBookingExecutionTool, ExecutionFeedback, PlaywrightBookingResult,
    AmapPoiResult
)

logger = logging.getLogger(__name__)


class AgentMode(Enum):
    HEALING = "healing"  # 治愈修复模式
    LIGHT = "light"      # 轻松放空模式  
    DEEP = "deep"        # 品质体验模式

@dataclass
class EmotionProfile:
    pressure_level: float  # 0-10
    energy_level: float    # 0-10
    last_preferred_vibe: str
    detected_keywords: List[str]

@dataclass
class VibeContext:
    vibe_score: float      # 0-10
    energy_level: float    # 0-10
    mode: AgentMode
    social_tendency: float # -5 to +5

@dataclass
class QuestNarrative:
    title: str
    role: str
    mission: str
    difficulty: str
    chips: List[str]
    duration: str
    reward: str


class LangGraphAgent:
    """
    LangGraph代理实现 - 基于PRD的慢生活轨道设计
    核心功能：情感感知 → 心境分析 → 独享任务生成
    """
    
    def __init__(self, supabase_client=None):
        self.checkpoint_data = {}
        self.emotion_memory = {}
        
        # 初始化工具类，捕获可能的初始化错误
        try:
            from services.data.scenario_generator import EnhancedScenarioGenerator
            self.scenario_generator = EnhancedScenarioGenerator()
        except Exception as e:
            logger.warning(f"EnhancedScenarioGenerator初始化失败，使用模拟模式: {e}")
            self.scenario_generator = None
            
        try:
            from services.tools.web_search_tool import WebSearchTool
            self.web_search_tool = WebSearchTool()  # 已初始化，用于Tavily实时检索
        except Exception as e:
            logger.warning(f"WebSearchTool初始化失败，使用模拟模式: {e}")
            self.web_search_tool = None
            
        try:
            self.booking_safety_gate = BookingSafetyGate()
        except Exception as e:
            logger.warning(f"BookingSafetyGate初始化失败，使用模拟模式: {e}")
            self.booking_safety_gate = None
            
        try:
            from services.tools.booking_execution_tool import PlaywrightBookingExecutionTool
            self.booking_execution_tool = PlaywrightBookingExecutionTool()  # 🆕 初始化地理工具
        except Exception as e:
            logger.warning(f"PlaywrightBookingExecutionTool初始化失败，使用模拟模式: {e}")
            self.booking_execution_tool = None

        # 使用传入的Supabase客户端或创建新的
        if supabase_client:
            self.supabase_client = supabase_client
        else:
            try:
                from db.supabase_client import SupabaseClient
                self.supabase_client = SupabaseClient()
            except Exception as e:
                logger.warning(f"SupabaseClient初始化失败，使用内存模式: {e}")
                self.supabase_client = None

        logger.info("LangGraph Agent 初始化完成（慢生活轨道模式）")

    async def _intercept_and_store_address(self, message: str, thread_state: ThreadState) -> Dict[str, Any]:
        """
        三步动作：
        1. 从用户当前message中尝试提取地址
        2. 与thread_state.metadata中存量地址比对校验
        3. 若不存在，返回"AI询问地点"的候选句
        
        返回结构：
        {
          "address_exists": bool,
          "address_value": Optional[str],
          "ai_ask_location_sentence": Optional[str],
          "lat": Optional[float],
          "lng": Optional[float]
        }
        """
        
        # 读历史槽位
        history_slot = thread_state.metadata.get("address_slot", {})
        history_location = history_slot.get("location")
        
        # 从用户当前输入简单提取地址（中文地址常见规律）
        location_patterns = [
            r'(在|到|去)(.*?)(附近|旁边|楼下|周围)',  # "我在三里屯soho附近"
            r'位于(.*?)(路|街|道|号)',               # "我位于朝阳区东三环中路5号"
            r'(.*?)(路|街|道)[0-9０-９]+号',        # "建国门外大街99号"
        ]
        
        current_location = None
        for pattern in location_patterns:
            match = re.search(pattern, message)
            if match:
                current_location = match.group(2) if len(match.groups()) > 1 else match.group(1)
                break  # 找到一个就停止
        if not current_location:
            # 更严格的地址提取：只在包含明确地名关键词时才提取
            location_keywords = [
                '三里屯', '西单', '王府井', '后海', '五道口', '朝阳公园', '国贸', '建国门', '四惠', '望京',
                '中关村', '天安门', '鼓楼', '南锣鼓巷', '簋街', '工体', '亚运村', '亦庄', '通州', '丰台',
                '地铁', '站', '村', '街', '路', '道', '胡同', '巷', '里', '村', '镇', '乡', '区', '县'
            ]
            
            # 检查消息中是否包含任何地理位置关键词
            found_keywords = []
            for keyword in location_keywords:
                if keyword in message:
                    found_keywords.append(keyword)
                    break
            
            # 只有找到明确的地理位置关键词时才尝试提取
            if found_keywords:
                # 使用更精确的模式匹配实际的地点名称
                for keyword in found_keywords:
                    # 查找包含关键词的短语
                    location_match = re.search(f'([^\\s，。！？]*{keyword}[^\\s，。！？]*)', message)
                    if location_match:
                        extracted_location = location_match.group(1)
                        
                        # 检查是否包含否定词汇
                        negation_patterns = [
                            f"(不|没|非|无)在.*{extracted_location}",
                            f"{extracted_location}.*(不|没|非|无)在",
                            f"(远离|避开|离开){extracted_location}",
                            f"不.*去.*{extracted_location}",
                            f"没.*去.*{extracted_location}"
                        ]
                        
                        is_negated = False
                        for pattern in negation_patterns:
                            if re.search(pattern, message):
                                is_negated = True
                                logger.info(f"检测到否定表达：{message}，跳过位置'{extracted_location}'")
                                break
                        
                        if not is_negated:
                            current_location = extracted_location
                            logger.info(f"提取到有效位置：{extracted_location}")
                        else:
                            logger.info(f"检测到否定表达，不提取位置：{extracted_location}")
                        break
            
            if not current_location:
                logger.info(f"未在消息中找到有效位置信息：{message}")
        
        # 若新位置存在且跟历史不一致，则覆盖
        if current_location and current_location != history_location:
            history_slot = {
                "location": current_location,
                "lat": None,  # 将在分支A中通过Geo API注入
                "lng": None,
                "updated_at": datetime.now().isoformat()
            }
            thread_state.metadata["address_slot"] = history_slot
            logger.info(f"更新地址槽位: {current_location} (覆盖历史: {history_location})")
        
        # 重新读取更新后的地址槽位
        address_exists = bool(thread_state.metadata.get("address_slot", {}).get("location"))
        if address_exists:
            return {
                "address_exists": True,
                "address_value": history_slot["location"],
                "lat": history_slot.get("lat"),
                "lng": history_slot.get("lng"),
                "ai_ask_location_sentence": None
            }
        
        # 若地址槽位为空，根据用户情绪生成询问语句（分支B - 协议v2优化）
        # 先共情再询问，让用户感到关怀而非机械
        empathy_prefix = "能理解你现在的感受"
        if any(word in message for word in ["不好", "难受", "压抑", "沮丧", "不开心", "郁闷"]):
            empathy_prefix = "看到你现在心情不太好，我很关心你"
        elif any(word in message for word in ["累", "疲劳", "疲惫"]):
            empathy_prefix = "感到疲惫的时候确实需要找个安静的地方休息"
        
        location_questions = [
            f"{empathy_prefix}，你在哪个区域呢？我帮你找找附近有什么治愈的好地方～",
            f"{empathy_prefix}，能告诉我你在哪个地铁站附近吗？我来为你寻找合适的去处～",
            f"{empathy_prefix}，你现在在哪个区域？我查查附近有什么适合放松的地方呢～",
            f"不论你现在在哪里，{empathy_prefix}。告诉我你的位置，我来为你找找好去处～"
        ]
        
        return {
            "address_exists": False,
            "address_value": None,
            "lat": None,
            "lng": None,
            "ai_ask_location_sentence": random.choice(location_questions)
        }
    
    async def process_message(self, message: str, thread_state: ThreadState) -> Dict[str, Any]:
        """
        基于PRD的慢生活轨道消息处理流程
        情感感知 → 心境分析 → 独享任务生成
        """
        logger.info(f"处理消息: {message}")
        
        # 🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕
        # Step 4.1: 先从Supabase load历史metadata，存到ThreadState (如果未缓存)
        if self.supabase_client and not thread_state.metadata:
            try:
                history = await self.supabase_client.load_thread_state(thread_state.thread_id)
                if history:
                    thread_state.metadata.update(history)
                    logger.info(f"已加载线程{thread_state.thread_id}历史metadata")
            except Exception as e:
                logger.warning(f"Supabase load失败(忽略): {e}")
        
        # 1. 情感记忆层处理
        emotion_profile = await self._emotion_sensing(message, thread_state)
        
        # 2. 氛围强度评估
        vibe_context = await self._vibe_intensity_assessment(emotion_profile, thread_state)
        
        # Step 1: 从当前消息中提取地址并更新state
        address_result = await self._intercept_and_store_address(message, thread_state)
        
        # Step 2: 基于地址处理结果做决策（Protocol v2.0 修复）  
        if not address_result["address_exists"]:
            # 分支B: 地址不存在，温柔询问（保护隐私，只问地铁站或区域）
            return {
                "type": "clarification",
                "empathy_response": address_result["ai_ask_location_sentence"],
                "requires_clarification": True,
                "address_query": True,
            }
        
        # 3. 轻柔澄清循环 (如果需要)
        if self._needs_clarification(message, emotion_profile):
            clarification = await self._gentle_clarification_flow(vibe_context)
            return {
                "type": "clarification",
                "empathy_response": clarification.empathy,
                "options": clarification.options,
                "requires_clarification": True
            }
        
        # 4. 共情响应生成
        empathy_response = await self._affective_empathy_engine(message, emotion_profile, vibe_context)
        
        # 5. 独享任务映射
        quest_narrative = await self._solo_friendly_quest_mapper(vibe_context, message)
        
        # 🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕
        # Step 1: 通过高德Geo注入坐标（如果尚未注入）
        if address_result["lat"] is None or address_result["lng"] is None:
            location_coords = await self.booking_execution_tool.get_location_by_query(
                thread_state.metadata["address_slot"]["location"]
            )
            if location_coords:
                thread_state.metadata["address_slot"]["lat"] = location_coords["lat"]
                thread_state.metadata["address_slot"]["lng"] = location_coords["lng"]
                logger.info(f"通过Geo注入位置: {thread_state.metadata['address_slot']['location']} (lat={location_coords['lat']}, lng={location_coords['lng']})")
        
        # 🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕
        # Step 2: 先用小范围POI搜索获取附近的候选商家
        initial_plans = []
        lat = thread_state.metadata["address_slot"].get("lat")
        lng = thread_state.metadata["address_slot"].get("lng")
        
        if lat and lng:
            nearby_pois = await self.booking_execution_tool.route_query_to_pois(
                thread_state.metadata["address_slot"]["location"],
                radius=1000,
                results_limit=8
            )
            
            for poi in nearby_pois:
                try:
                    lng_str, lat_str = poi.location.split(',')
                    poi_lat = float(lat_str)
                    poi_lng = float(lng_str)
                except (ValueError, AttributeError):
                    poi_lat = lat
                    poi_lng = lng
                
                initial_plans.append({
                    "merchant_name": poi.name,
                    "merchant_address": poi.address,
                    "lat": poi_lat,
                    "lng": poi_lng,
                    "distance": poi.distance if hasattr(poi, "distance") else None,
                    "rating": float(poi.rating) if poi.rating and poi.rating.replace('.', '').isdigit() else None,
                })
        
        # Step 3: 对POI候选商家进行实时信息检索
        enhanced_plans = await self._batch_real_time_info_retrieval(initial_plans, message)
        
        # Step 4: 基于实时检索结果生成详细方案
        detailed_scenario = await self._generate_enhanced_detailed_scenario(
            vibe_context, message, quest_narrative, enhanced_plans
        )
        
        # 5. 批量实时信息检索结果写入方案
        if enhanced_plans and hasattr(detailed_scenario, "plans"):
            detailed_scenario.plans = enhanced_plans
        
        # 6. 实时补充检索（单商户深度信息，可选）
        updated_scenario = await self._real_time_info_retrieval(detailed_scenario, message)
        
        # 8. 预订需求评估
        booking_assessment = await self._assess_booking_requirements(updated_scenario, message)
        
        # 8. 匿名共鸣集成
        copresence_info = await self._generate_copresense_enhancement(thread_state)
        
        # 保存完整的状态检查点
        # 序列化详细方案为字典，确保可以被JSON序列化
        serialized_scenario = None
        if detailed_scenario:
            try:
                from dataclasses import asdict
                import json
                
                # 序列化为字典后进行JSON兼容性处理
                scenario_dict = asdict(detailed_scenario) if hasattr(detailed_scenario, '__dataclass_fields__') else detailed_scenario
                
                # 深度转换以处理嵌套的枚举
                def convert_enums(obj):
                    if isinstance(obj, dict):
                        return {k: convert_enums(v) for k, v in obj.items()}
                    elif isinstance(obj, list):
                        return [convert_enums(item) for item in obj]
                    elif hasattr(obj, 'value'):  # 处理枚举
                        return obj.value
                    else:
                        return obj
                
                scenario_dict = convert_enums(scenario_dict)
                
                # 测试JSON序列化
                json.dumps(scenario_dict)
                serialized_scenario = scenario_dict
            except Exception as e:
                logger.warning(f"序列化详细方案失败: {e}，使用字符串表示")
                serialized_scenario = str(detailed_scenario)
        
        serialized_updated_scenario = None
        if updated_scenario:
            try:
                # 同样处理更新方案
                updated_dict = asdict(updated_scenario) if hasattr(updated_scenario, '__dataclass_fields__') else updated_scenario
                
                def convert_enums(obj):
                    if isinstance(obj, dict):
                        return {k: convert_enums(v) for k, v in obj.items()}
                    elif isinstance(obj, list):
                        return [convert_enums(item) for item in obj]
                    elif hasattr(obj, 'value'):  # 处理枚举
                        return obj.value
                    else:
                        return obj
                
                updated_dict = convert_enums(updated_dict)
                json.dumps(updated_dict)
                serialized_updated_scenario = updated_dict
            except Exception as e:
                logger.warning(f"序列化更新方案失败: {e}，使用字符串表示")
                serialized_updated_scenario = str(updated_scenario)
        
        await self._save_enhanced_checkpoint(thread_state.thread_id, {
            "emotion_profile": asdict(emotion_profile),
            "vibe_context": {
                "vibe_score": vibe_context.vibe_score,
                "energy_level": vibe_context.energy_level,
                "mode": vibe_context.mode.value,  # 转换为字符串
                "social_tendency": vibe_context.social_tendency
            },
            "quest_narrative": asdict(quest_narrative),
            "detailed_scenario": serialized_scenario,
            "updated_scenario": serialized_updated_scenario,
            "booking_assessment": booking_assessment,
            "copresence": copresence_info,
            "last_message": message
        })
        
        # 🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕
        # Step 4.2: 处理完后把地址等信息persist到Supabase (下一次对话不丢失)
        if self.supabase_client:
            try:
                await self.supabase_client.save_thread_state(thread_state.thread_id, thread_state.metadata)
            except Exception as e:
                logger.warning(f"Supabase save失败(忽略): {e}")
        
        # 转换详细方案为API格式
        api_scenario = self.scenario_generator.convert_to_api_format(detailed_scenario)
        
        # 更新方案包含实时信息（如果获取成功）
        final_scenario = api_scenario
        if updated_scenario and hasattr(updated_scenario, 'detailed_scenario'):
            final_scenario = updated_scenario  # 使用更新后的方案
        
        result = {
            "type": "complete_response",
            "empathy_response": empathy_response,
            "quest": asdict(quest_narrative),
            "detailed_scenario": final_scenario,
            "copresence": copresence_info,
            "requires_confirmation": False  # 默认不需要确认
        }
        
        # 添加预订相关信息（如果需要预订）
        if booking_assessment and booking_assessment.get("requires_booking"):
            result["booking_info"] = booking_assessment
            result["requires_confirmation"] = booking_assessment.get("needs_confirmation", False)
        
        # 添加地址状态信息，供上层使用(Protocol v2.0 修复)
        result["address_status"] = {
            "has_location": address_result["address_exists"],
            "location": address_result["address_value"]
        }
        
        return result

    async def _emotion_sensing(self, message: str, thread_state: ThreadState) -> EmotionProfile:
        """情感感知节点 - 分析用户心境状态"""
        message_lower = message.lower()
        
        # 检测压力关键词
        pressure_keywords = ['累', '疲', '倦', '压力', '焦虑', '烦躁', '不开心', '抑郁', '内耗']
        energy_keywords = ['想出门', '活力', '精神', '能量', '兴奋', '好奇', '探索']
        
        detected_keywords = []
        pressure_score = 0
        energy_score = 5  # 默认中性
        
        # 分析压力水平
        for keyword in pressure_keywords:
            if keyword in message_lower:
                detected_keywords.append(keyword)
                pressure_score += 1.5
        
        # 分析能量水平
        for keyword in energy_keywords:
            if keyword in message_lower:
                detected_keywords.append(keyword)
                energy_score += 1.0
                pressure_score -= 0.5
        
        # 从历史记录中获取偏好
        last_vibe = "安静角落"
        if thread_state.metadata.get("last_successful_vibe"):
            last_vibe = thread_state.metadata["last_successful_vibe"]
        
        # 限制范围
        pressure_level = max(0, min(10, pressure_score))
        energy_level = max(0, min(10, energy_score))
        
        logger.info(f"情感分析结果 - 压力: {pressure_level}, 能量: {energy_level}")
        
        return EmotionProfile(
            pressure_level=pressure_level,
            energy_level=energy_level,
            last_preferred_vibe=last_vibe,
            detected_keywords=detected_keywords
        )

    async def _vibe_intensity_assessment(self, emotion: EmotionProfile, 
                                        thread_state: ThreadState) -> VibeContext:
        """氛围强度评估 - 计算Vibe Score并确定模式"""
        # 基于PRD的Vibe Score计算公式
        vibe_score = (10 - emotion.pressure_level) * 0.7 + emotion.energy_level * 0.3
        vibe_score = max(0, min(10, vibe_score))
        
        # 确定模式
        if vibe_score <= 3:
            mode = AgentMode.HEALING
        elif vibe_score <= 6:
            mode = AgentMode.LIGHT
        else:
            mode = AgentMode.DEEP
            
        # 分析社交倾向（基于历史）
        social_tendency = 0  # 偏向独处
        hist_messages = thread_state.messages
        social_indicators = [msg for msg in hist_messages if "社交" in msg.get("content", "")]
        if len(social_indicators) > 2:
            social_tendency = min(2, len(social_indicators) * 0.5)
        
        logger.info(f"氛围评估 - Vibe Score: {vibe_score}, 模式: {mode.value}")
        
        return VibeContext(
            vibe_score=vibe_score,
            energy_level=emotion.energy_level,
            mode=mode,
            social_tendency=social_tendency
        )

    def _needs_clarification(self, message: str, emotion: EmotionProfile) -> bool:
        """判断是否需要澄清"""
        # 信息不足的情况
        vague_indicators = ['不知道', '?', '哪里', '什么', '随便']
        needs_clarification = any(indicator in message for indicator in vague_indicators)
        
        # 极低能量时需要更多引导
        if emotion.energy_level <= 2:
            return True
            
        return needs_clarification

    async def _gentle_clarification_flow(self, vibe_context: VibeContext):
        """轻柔澄清循环"""
        class ClarificationResult:
            def __init__(self, empathy: str, options: list):
                self.empathy = empathy
                self.options = options
        
        # 根据模式提供不同选项
        if vibe_context.mode == AgentMode.HEALING:
            empathy = "听起来您现在就想要一个安静的地方放松一下呢🌿"
            options = [
                "📍 就在附近找个安静的角落",
                "☕ 推荐一家一个人友好的咖啡店",
                "🌳 公园散步治愈一下心情"
            ]
        elif vibe_context.mode == AgentMode.LIGHT:
            empathy = "想出来走走很不错呀！您今天的心情更适合哪种体验呢～"
            options = [
                "🎵 轻松的音乐小馆坐一坐",
                "📚 安静的书店翻翻书",
                "🍵 找个地方慢慢喝茶"
            ]
        else:
            empathy = "充满能量的一天！想要什么样的深度体验呢？"
            options = [
                "🎨 去艺术区走走看看",
                "📝 找个地方写点东西或画画",
                "🎯 探索一个有趣的新地方"
            ]
        
        return ClarificationResult(empathy, options)

    async def _affective_empathy_engine(self, message: str, emotion: EmotionProfile, 
                                       vibe_context: VibeContext) -> str:
        """共情引擎 - 生成个性化回应"""
        empathy_templates = {
            AgentMode.HEALING: [
                "我知道你最近有些累了，抱抱你🫂。其实不需要做多么宏大的计划，就在附近找个安静的角落也很好...",
                "感受到了你想放松的心情🌿。一个人静静地待会儿，听点音乐或者看看窗外的风景就很治愈了。",
                "放空完全不需要花很多钱。去公园的长椅上看夕阳，或者带上一杯温水散步，都是很棒的独处时光。"
            ],
            AgentMode.LIGHT: [
                "一个人的小出走最棒了！既不用考虑别人的感受，也不用社交压力，就按照自己的节奏来～",
                "你提到的很打动我，这就是美好的独处时光呢💛。我来为你准备一些轻松的选择。",
                "偶尔给自己一段完全属于自己的时间真的很重要。你是很棒的独处艺术家！"
            ],
            AgentMode.DEEP: [
                "感觉到你今天的能量很棒！想要深度探索的感觉，我很欣赏这种主动的精神🌟",
                "很棒的灵感！一个人的时候思维最清晰，是进行创作和思考的黄金时光。",
                "一个人的冒险最刺激了！不用担心同伴的感受，可以完全按自己的想法走。"
            ]
        }
        
        templates = empathy_templates[vibe_context.mode]
        selected_template = templates[hash(message) % len(templates)]
        
        logger.info(f"生成共情响应 - 模式: {vibe_context.mode.value}")
        return selected_template

    async def _solo_friendly_quest_mapper(self, vibe_context: VibeContext, 
                                         user_input: str) -> QuestNarrative:
        """独享任务映射器 - 将物理地点转化为叙事挑战"""
        quest_templates = {
            AgentMode.HEALING: {
                "title": "静谧午后：河边漫步与手冲咖啡",
                "role": "休憩者",
                "mission": "听歌、呼吸或观察，享受专属你的沉浸时光",
                "difficulty": "简单",
                "chips": ["低压力", "一个人友好", "附近可完成"],
                "duration": "30分钟内的治愈时光",
                "reward": "点亮今日出门徽章"
            },
            AgentMode.LIGHT: {
                "title": "城市角落的慢时光收集",
                "role": "观察者",
                "mission": "记录并收集3个有趣的生活细节",
                "difficulty": "适中",
                "chips": ["灵感收集", "慢行探索", "心境记录"],
                "duration": "45分钟的轻松漫游",
                "reward": "解锁全新城市角落"
            },
            AgentMode.DEEP: {
                "title": "独自出发的艺术探险",
                "role": "都市探索者",
                "mission": "在限定时间内完成一次心灵启发之旅",
                "difficulty": "深度体验",
                "chips": ["高品质探索", "专注修行", "独享空间"],
                "duration": "90分钟的沉浸体验",
                "reward": "获得都市漫步者勋章"
            }
        }
        
        template = quest_templates[vibe_context.mode]
        
        # 基于用户输入微调任务描述
        if "咖啡" in user_input:
            template["title"] = "一个人的咖啡时光艺术"
            template["mission"] = "在手冲咖啡的香气中享受独处的静谧"
        elif "公园" in user_input or "自然" in user_input:
            template["title"] = "自然疗愈漫步计划"
            template["mission"] = "在自然的怀抱中重新连接自己的内心"
        
        logger.info(f"生成独享任务 - 标题: {template['title']}")
        return QuestNarrative(**template)

    async def _difficulty_adapter_and_generator(self, quest: QuestNarrative, 
                                               vibe_context: VibeContext) -> QuestNarrative:
        """难度自适应调整器"""
        # 根据能量水平动态调整
        if vibe_context.energy_level <= 3:
            # 极低能量 - 强制降级
            quest.difficulty = "特别简单"
            quest.chips.append("特别轻松")
            quest.duration = "15-20分钟的微体验"
            quest.mission = "只需要简单地出门走走，不用强求完美"
        
        elif vibe_context.energy_level >= 8:
            # 高能量 - 可以挑战
            quest.chips.append("挑战自我")
            
        # 如果压力水平高，移除任何有压力的标签
        if vibe_context.mode == AgentMode.HEALING:
            quest.chips = [chip for chip in quest.chips if "挑战" not in chip and "压力" not in chip]
            quest.chips.append("零压力")
        
        logger.info(f"难度自适应调整完成 - 新难度: {quest.difficulty}")
        return quest
    
    async def _generate_detailed_scenario(self, 
                                        vibe_context, 
                                        user_message: str, 
                                        quest_narrative) -> Any:
        """生成详细完整方案"""
        # 根据心境选择合适的方案模式
        mode_mapping = {
            "healing": "healing",
            "light": "healing", 
            "deep": "exploration"
        }
        
        scenario_mode = mode_mapping.get(vibe_context.mode.value, "healing")
        
        # 生成完整详细的出游场景
        detailed_scenario = self.scenario_generator.generate_complete_enhanced_scenario(
            user_message, scenario_mode
        )
        
        logger.info(f"详细方案生成完成 - 商家: {detailed_scenario.merchant.name}")
        return detailed_scenario
    
    async def _real_time_info_retrieval(self, 
                                      detailed_scenario: Any,
                                      user_message: str) -> Dict[str, Any]:
        """实时信息检索节点 - 获取商家最新状态"""
        # 检查是否为有效的详细方案对象
        if not hasattr(detailed_scenario, 'merchant'):
            logger.info("跳过实时信息检索 - 无详细方案数据")
            return detailed_scenario
        
        # 延迟初始化Web搜索工具
        if self.web_search_tool is None:
            self.web_search_tool = WebSearchTool()
        
        try:
            merchant_name = detailed_scenario.merchant.name
            merchant_address = detailed_scenario.merchant.location.address
            
            if not merchant_name or not merchant_address:
                logger.info("跳过实时信息检索 - 缺少商家信息")
                return detailed_scenario
            
            logger.info(f"开始检索实时信息 - 商家: {merchant_name}")
            
            # 创建异步上下文
            async with self.web_search_tool as search_tool:
                # 搜索商家营业状态
                status_query = SearchQuery(
                    query=merchant_name,
                    location=merchant_address,
                    search_type="business_status"
                )
                
                business_info = await search_tool.search_business_info(status_query)
                
                # 如果商家当前关闭或状态异常，更新方案
                if not business_info.is_open or business_info.current_status != "open":
                    logger.info(f"商家状态异常 - {merchant_name}: {business_info.current_status}")
                    
                    # 更新方案信息
                    updated_scenario = detailed_scenario.copy() if hasattr(detailed_scenario, 'copy') else dict(detailed_scenario) if hasattr(detailed_scenario, 'keys') else detailed_scenario
                    updated_scenario['merchant_info']['real_time_status'] = {
                        'is_open': business_info.is_open,
                        'current_status': business_info.current_status,
                        'last_updated': business_info.last_updated,
                        'safety_info': business_info.safety_info
                    }
                    
                    # 添加特殊提示
                    if not business_info.is_open:
                        updated_scenario['merchant_info']['recommendations'] = [
                            "商家当前暂未营业，建议改期前往",
                            f"营业时间建议致电确认: {detailed_scenario.get('merchant_info', {}).get('contact', '未提供') if hasattr(detailed_scenario, 'get') else '未提供'}",
                            "或选择备选方案"
                        ]
                    
                    return updated_scenario
        
        except Exception as e:
            logger.error(f"实时信息检索失败: {e}")
            # 实时信息获取失败不影响整体流程，返回原始方案
        
        return detailed_scenario
    
    async def _assess_booking_requirements(self, 
                                         detailed_scenario: Any,
                                         user_message: str) -> Optional[Dict[str, Any]]:
        """评估预订需求 - 判断是否需要执行预订"""
        # 获取商家和费用信息
        if not detailed_scenario:
            logger.info("预订评估：无详细方案数据，跳过预订评估")
            return None
        
        try:
            merchant_info = {
                'name': detailed_scenario.merchant.name,
                'address': detailed_scenario.merchant.location.address,
                'type': detailed_scenario.merchant.type.value,
                'contact': detailed_scenario.merchant.contact
            }
            cost_info = {
                'consumption': detailed_scenario.cost_breakdown.consumption,
                'total': detailed_scenario.cost_breakdown.total
            }
            
            # 判断是否需要预订
            booking_indicators = [
                "预订" in user_message or "预约" in user_message,
                cost_info.get('consumption', 0) > 50,  # 消费超过50元
                merchant_info.get('type') in ['咖啡店', '餐厅'],  # 需要预订的场所
                "指定时间" in user_message or "特定时间" in user_message
            ]
            
            if not any(booking_indicators):
                logger.info("无需预订 - 用户未明确要求或不符合预订条件")
                return None
            
            # 构建预订请求
            booking_request = BookingRequest(
                booking_type=self._map_merchant_type_to_booking(merchant_info.get('type')),
                merchant_name=merchant_info.get('name', ''),
                location=merchant_info.get('address', ''),
                estimated_cost=float(cost_info.get('consumption', 0)),
                planned_time=datetime.now().isoformat(),  # 默认现在
                estimated_duration=90,  # 默认90分钟
                requires_external_api=True,
                # api_provider="",  # 不再使用美团API
                special_requirements=self._extract_special_requirements(user_message)
            )
            
            # 执行风险评估
            risk_assessment = await self.booking_safety_gate.assess_booking_risk(booking_request)
            
            assessment_result = {
                "requires_booking": True,
                "needs_confirmation": risk_assessment.requires_confirmation,
                "risk_level": risk_assessment.overall_level.value,
                "risk_score": risk_assessment.risk_score,
                "booking_request": {
                    "type": booking_request.booking_type.value,
                    "merchant": booking_request.merchant_name,
                    "estimated_cost": booking_request.estimated_cost,
                    "planned_time": booking_request.planned_time
                },
                "risk_assessment": {
                    "level": risk_assessment.overall_level.value,
                    "factors": [factor.__dict__ for factor in risk_assessment.risk_factors],
                    "recommendation": risk_assessment.recommendation,
                    "mitigation_suggestions": risk_assessment.mitigation_suggestions
                }
            }
            
            logger.info(f"预订需求评估完成 - 需要确认: {risk_assessment.requires_confirmation}")
            return assessment_result
            
        except Exception as e:
            logger.error(f"预订需求评估失败: {e}")
            return {
                "requires_booking": False,
                "error": f"预订评估失败: {str(e)}"
            }
    
    def _map_merchant_type_to_booking(self, merchant_type: str) -> BookingType:
        """映射商家类型到预订类型"""
        type_mapping = {
            "咖啡店": BookingType.RESTAURANT,
            "餐厅": BookingType.RESTAURANT,
            "健身中心": BookingType.ENTERTAINMENT,
            "艺术中心": BookingType.ENTERTAINMENT,
            "SPA中心": BookingType.ENTERTAINMENT
        }
        return type_mapping.get(merchant_type, BookingType.RESTAURANT)
    
    def _extract_special_requirements(self, user_message: str) -> List[str]:
        """从用户消息中提取特殊要求"""
        requirements = []
        
        requirement_patterns = {
            "靠窗位置": ["靠窗", "窗户", "窗边"],
            "安静位置": ["安静", "僻静", "不被打扰"],
            "预订座位": ["预订座位", "预留位置"],
            "特殊饮食": ["素食", "无糖", "过敏"],
            "庆祝活动": ["生日", "庆祝", "浪漫"]
        }
        
        for requirement, patterns in requirement_patterns.items():
            if any(pattern in user_message for pattern in patterns):
                requirements.append(requirement)
        
        return requirements
    
    def _check_execution_safety(self, scenario) -> bool:
        """检查执行安全性 - 判断是否需要HITL确认"""
        # 高风险判断标准
        risk_indicators = []
        
        # 检查费用超过阈值
        if hasattr(scenario, 'cost_breakdown'):
            if scenario.cost_breakdown.total > 100:
                risk_indicators.append("费用较高")
        
        # 检查时长过长
        if hasattr(scenario, 'route'):
            if scenario.route.total_duration > 180:  # 3小时以上
                risk_indicators.append("时间过长")
        
        # 检查商家类型是否需要确认
        high_risk_types = ["艺术中心", "博物馆", "高端餐厅"]
        if scenario.merchant.type.value in high_risk_types:
            risk_indicators.append("特殊体验类型")
        
        return len(risk_indicators) > 0

    async def _generate_copresense_enhancement(self, thread_state: ThreadState) -> dict:
        """生成匿名共鸣增强信息"""
        # 模拟同城数据
        import random
        
        city_totals = random.randint(150, 350)
        nearby_count = random.randint(8, 25)
        
        companion_routes = [
            {"name": "咖啡散步线", "vibe": "治愈 | 安静", "count": random.randint(10, 18)},
            {"name": "公园漫步线", "vibe": "自然 | 放松", "count": random.randint(15, 30)},
            {"name": "书店探索线", "vibe": "文艺 | 思考", "count": random.randint(5, 12)}
        ]
        
        return {
            "today_total": city_totals,
            "nearby_count": nearby_count,
            "companion_routes": companion_routes,
            "message": f"今天同城已有 {city_totals} 人漫游出门，附近 3km 有 {nearby_count} 人正在独处打卡中"
        }

    # 已更新为使用详细方案的安全检查方法

    async def _save_enhanced_checkpoint(self, thread_id: str, state_data: dict) -> bool:
        """保存增强检查点到 Supabase 数据库"""
        checkpoint_id = f"checkpoint-{datetime.utcnow().timestamp()}"
        
        checkpoint_data = CheckpointData(
            thread_id=thread_id,
            checkpoint_id=checkpoint_id,
            state=state_data,
            timestamp=datetime.utcnow().isoformat()
        )
        
        try:
            # 优先保存到 Supabase 数据库（持久化）
            if self.supabase_client:
                success = await self.supabase_client.save_checkpoint(checkpoint_data)
                if success:
                    logger.info(f"增强检查点 {checkpoint_id} 已保存到 Supabase 数据库")
                else:
                    logger.error(f"保存检查点 {checkpoint_id} 到 Supabase 失败，回退到内存")
                    # 回退到内存存储
                    self.checkpoint_data[checkpoint_id] = checkpoint_data
            else:
                logger.warning("Supabase 客户端未初始化，使用内存存储")
                self.checkpoint_data[checkpoint_id] = checkpoint_data
            
            # 同时保存情感记忆
            self.emotion_memory[thread_id] = state_data.get("emotion_profile")
            
            logger.info(f"增强检查点 {checkpoint_id} 保存完成")
            return True
            
        except Exception as e:
            logger.error(f"保存增强检查点 {checkpoint_id} 时出错: {e}")
            # 异常时回退到内存
            self.checkpoint_data[checkpoint_id] = checkpoint_data
            return False

    def _detect_intent(self, message: str) -> str:
        """保持向后兼容的意图检测方法"""
        message_lower = message.lower()
        
        intent_patterns = {
            "wander_planning": ["想去", "想找", "计划", "安排", "推荐", "地方"],
            "emotional_support": ["心情", "感觉", "难受", "开心", "孤独", "放松"],
            "solitude_seeking": ["一个人", "独自", "安静", "独处", "不想说话"],
            "healing_request": ["累", "疲", "倦", "需要休息", "想放松"]
        }
        
        for intent, patterns in intent_patterns.items():
            if any(pattern in message_lower for pattern in patterns):
                return intent
        
        return "slow_life_exploration"
    
    def _generate_response_plan(self, intent: str, message: str) -> Dict[str, Any]:
        """根据意图生成响应计划"""
        
        base_plan = {
            "empathy_response": "",
            "suggested_actions": [],
            "needs_user_input": False
        }
        
        if intent == "wander_planning":
            base_plan.update({
                "empathy_response": f"我理解您想要独自探索的想法，'{message}' 听起来是个不错的计划。",
                "suggested_actions": [
                    {
                        "type": "wander_plan",
                        "data": {
                            "id": "wander-plan-001",
                            "title": "独自咖啡时光",
                            "category": "休闲放松",
                            "duration": "2小时",
                            "cost": "¥50-80",
                            "area": "三里屯",
                            "quote": "一个人也要好好生活",
                            "highlightTag": "一人友好",
                            "subChips": ["安静", "WiFi", "插座"],
                            "description": "找到一家温馨的独立咖啡店，享受属于自己的静谧时光",
                            "image": "/coffee-shop.jpg"
                        }
                    }
                ],
                "needs_user_input": True
            })
        
        elif intent == "emotional_support":
            base_plan.update({
                "empathy_response": f"听起来您现在的感受是：{message}。让我为您提供一些舒缓心情的建议。",
                "suggested_actions": [
                    {
                        "type": "emotional_support",
                        "data": {
                            "suggestions": ["深呼吸练习", "听轻音乐", "写日记", "散步"]
                        }
                    }
                ],
                "needs_user_input": False
            })
        
        elif intent == "social_interaction":
            base_plan.update({
                "empathy_response": f"想要认识新朋友或参与互动很棒！'{message}'。",
                "suggested_actions": [
                    {
                        "type": "social_activity",
                        "data": {
                            "activity": "轻量PK挑战",
                            "description": "参与今天的轻量PK挑战，结识志同道合的朋友"
                        }
                    }
                ],
                "needs_user_input": True
            })
        
        else:
            base_plan.update({
                "empathy_response": f"我听到了您的想法：'{message}'。我很乐意帮助您。",
                "suggested_actions": [
                    {
                        "type": "general_assistance",
                        "data": {
                            "offer_help": "我可以为您推荐地方、提供情感支持或安排活动"
                        }
                    }
                ],
                "needs_user_input": False
            })
        
        return base_plan
    
    def _requires_confirmation(self, plan: Dict[str, Any]) -> bool:
        """判断计划是否需要用户确认"""
        # 需要确认的场景：
        # 1. 涉及预订/消费的活动
        # 2. 社交互动
        # 3. 用户明确需要输入的活动
        
        if plan.get("needs_user_input", False):
            return True
        
        for action in plan.get("suggested_actions", []):
            action_type = action.get("type", "")
            if action_type in ["wander_plan", "social_activity", "booking"]:
                # 检查是否涉及费用
                action_data = action.get("data", {})
                if "cost" in action_data or action_type == "booking":
                    return True
        
        return False
    
    async def _save_checkpoint(self, thread_id: str, state: Dict[str, Any]) -> bool:
        """保存检查点状态到 Supabase 数据库（向后兼容）"""
        checkpoint_id = f"checkpoint-{datetime.utcnow().timestamp()}"
        
        checkpoint_data = CheckpointData(
            thread_id=thread_id,
            checkpoint_id=checkpoint_id,
            state=state,
            timestamp=datetime.utcnow().isoformat()
        )
        
        try:
            # 优先保存到 Supabase 数据库
            if self.supabase_client:
                success = await self.supabase_client.save_checkpoint(checkpoint_data)
                if success:
                    logger.info(f"检查点 {checkpoint_id} 已保存到 Supabase 数据库")
                    return True
                else:
                    logger.error(f"保存检查点 {checkpoint_id} 到 Supabase 失败")
            
            # 回退到内存存储
            self.checkpoint_data[checkpoint_id] = checkpoint_data
            logger.info(f"检查点 {checkpoint_id} 已保存到内存（回退）")
            return True
            
        except Exception as e:
            logger.error(f"保存检查点 {checkpoint_id} 时出错: {e}")
            # 异常时回退到内存
            self.checkpoint_data[checkpoint_id] = checkpoint_data
            return False
    
    async def restore_from_checkpoint(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """从检查点恢复状态"""
        if checkpoint_id in self.checkpoint_data:
            checkpoint = self.checkpoint_data[checkpoint_id]
            logger.info(f"从检查点 {checkpoint_id} 恢复状态")
            return checkpoint.state
        
        logger.warning(f"检查点 {checkpoint_id} 未找到")
        return None
    
    async def resume_execution(self, thread_state: ThreadState, user_confirmation: bool = True) -> Dict[str, Any]:
        """恢复中断的执行（用户确认后）"""
        logger.info(f"恢复thread {thread_state.thread_id} 的执行")
        
        # 模拟恢复执行
        if user_confirmation:
            return {
                "status": "resumed",
                "message": "基于您的确认，继续执行计划",
                "next_actions": ["执行预订", "发送详细信息", "更新状态"]
            }
        else:
            return {
                "status": "cancelled",
                "message": "用户取消了操作",
                "next_actions": ["重新规划", "询问新需求"]
        }

    async def _batch_real_time_info_retrieval(self, plans: List[Dict], user_message: str) -> List[Dict]:
        """批量实时信息检索 - 对附近商家进行批量状态查询"""
        if not plans or len(plans) == 0:
            logger.info("跳过批量实时检索 - 无候选商家")
            return plans
        
        # 延迟初始化Web搜索工具
        if self.web_search_tool is None:
            self.web_search_tool = WebSearchTool()
        
        enhanced_plans = []
        
        try:
            for plan in plans:
                try:
                    merchant_name = plan.get("merchant_name", "")
                    merchant_address = plan.get("merchant_address", "")
                    
                    if not merchant_name:
                        logger.warning(f"跳过商家 - 无名称: {plan}")
                        enhanced_plans.append(plan)
                        continue
                    
                    logger.info(f"批量检索实时信息 - 商家: {merchant_name}")
                    
                    # 搜索商家营业状态
                    status_query = SearchQuery(
                        query=merchant_name,
                        location=merchant_address,
                        search_type="business_status"
                    )
                    
                    try:
                        # 使用异步上下文管理器确保session正确初始化(Protocol v2.0修复)
                        async with self.web_search_tool as search_tool:
                            business_info = await search_tool.search_business_info(status_query)
                        
                        # 如果实时检索成功，增强商家信息
                        logger.info(f"[DEBUG] 商家{merchant_name}返回的business_info: {business_info}, type: {type(business_info)}")
                        enhanced_plan = plan.copy()
                        if business_info and hasattr(business_info, 'is_open'):
                            enhanced_plan["real_time_status"] = {
                                "is_open": business_info.is_open,
                                "current_status": business_info.current_status,
                                "last_updated": datetime.utcnow().isoformat()
                            }
                            enhanced_plan["online_availability"] = business_info.is_open
                            logger.info(f"[DEBUG] 成功设置商家{merchant_name}的real_time_status")
                        else:
                            logger.warning(f"[DEBUG] business_info无效，使用默认值: {business_info}")
                            enhanced_plan["real_time_status"] = {
                                "is_open": True,
                                "current_status": "unknown",
                                "last_updated": datetime.utcnow().isoformat(),
                                "error": "business_info对象无效"
                            }
                        
                        enhanced_plans.append(enhanced_plan)
                        
                    except Exception as retrieval_error:
                        logger.warning(f"商家{merchant_name}实时检索失败: {retrieval_error}")
                        # 实时检索失败，保留原计划
                        plan["real_time_status"] = {
                            "is_open": True,  # 默认假设开放
                            "current_status": "unknown",
                            "last_updated": datetime.utcnow().isoformat(),
                            "error": "实时检索失败，使用默认状态"
                        }
                        enhanced_plans.append(plan)
                        
                except Exception as plan_error:
                    logger.error(f"处理商家信息时出错: {plan_error}")
                    # 出现错误也保留原计划
                    enhanced_plans.append(plan)
                    
        except Exception as batch_error:
            logger.error(f"批量实时检索整体失败: {batch_error}")
            # 发生严重错误时返回原始计划
            enhanced_plans = plans
        
        logger.info(f"批量实时检索完成 - 处理了{len(plans)}个商家，成功{len(enhanced_plans)}个")
        return enhanced_plans

    async def _generate_enhanced_detailed_scenario(self, 
                                                vibe_context, 
                                                user_message: str, 
                                                quest_narrative, 
                                                enhanced_plans: List[Dict] = None) -> Any:
        """基于实时检索结果生成增强详细方案"""
        # 根据心境选择合适的方案模式
        mode_mapping = {
            "healing": "healing",
            "light": "healing", 
            "deep": "exploration"
        }
        
        scenario_mode = mode_mapping.get(vibe_context.mode.value, "healing")
        
        # 过滤出可用的商家（仅开放状态）(Protocol v2.0修复)
        available_plans = []
        if enhanced_plans:
            for plan in enhanced_plans:
                real_time_status = plan.get("real_time_status", {})
                is_open = real_time_status.get("is_open", True)  # 默认开放
                current_status = real_time_status.get("current_status")
                
                # 宽松的可用性判断：有实时状态且开放，或者没有实时状态（降级情况）
                is_available = (
                    (not real_time_status and is_open) or  # 无实时状态，默认可用
                    (real_time_status and is_open and current_status in ["open", "unknown"])  # 有实时状态且开放
                )
                
                if is_available:
                    available_plans.append(plan)
                
                logger.info(f"[DEBUG] 商家过滤: {plan.get('merchant_name', '未知')} - 实时状态: {real_time_status}, 可用: {is_available}")
        
        logger.info(f"可用商家数量: {len(available_plans)} / {len(enhanced_plans) if enhanced_plans else 0}")
        
        # 如果有可用的实时商家，使用这些商家信息增强方案
        if available_plans:
            # 选择最佳商家（评分高的、距离近的）
            best_plan = self._select_best_merchant(available_plans)
            
            if best_plan and hasattr(self.scenario_generator, 'generate_with_plans'):
                # 使用实时商家信息生成方案
                detailed_scenario = self.scenario_generator.generate_with_plans(
                    user_message, scenario_mode, 
                    {
                        "selected_merchant": best_plan,
                        "alternative_merchants": available_plans[1:4] if len(available_plans) > 1 else []
                    }
                )
                logger.info(f"使用实时商家生成方案 - 商家: {best_plan.get('merchant_name', '未知')}")
            else:
                # 降级到标准方案生成
                detailed_scenario = self.scenario_generator.generate_complete_enhanced_scenario(
                    user_message, scenario_mode
                )
                logger.info("降级到标准方案生成")
        else:
            # 没有可用商家时，使用标准方案生成
            detailed_scenario = self.scenario_generator.generate_complete_enhanced_scenario(
                user_message, scenario_mode
            )
            logger.info("无实时商家可用，使用标准方案生成")
        
        logger.info(f"增强详细方案生成完成 - 模式: {scenario_mode}")
        return detailed_scenario
        
    def _select_best_merchant(self, available_plans: List[Dict]) -> Dict:
        """选择最佳商家（评分最高，距离最近）"""
        if not available_plans:
            return None
        
        def score_plan(plan):
            rating = plan.get("rating", 0) or 0
            distance = plan.get("distance", 999) or 999
            # 评分优先，距离次要
            return (rating * 1000) - (distance / 10)
        
        return max(available_plans, key=score_plan)

    def get_agent_status(self) -> Dict[str, Any]:
        """获取代理状态信息"""
        return {
            "total_checkpoints": len(self.checkpoint_data),
            "active_threads": len(set(
                cp.thread_id for cp in self.checkpoint_data.values()
            )),
            "last_activity": datetime.utcnow().isoformat()
        }
