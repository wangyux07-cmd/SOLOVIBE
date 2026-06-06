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

    async def _analyze_react_requirements(self, message: str, emotion_profile: EmotionProfile) -> Dict[str, Any]:
        """
        🎯 ReAct - Stage 1: Thought (推理分析)
        分析用户消息的复合需求，拆解情感需求和功能需求
        
        Args:
            message: 用户消息
            emotion_profile: 情感分析结果
            
        Returns:
            Dict: ReAct行动计划
        """
        try:
            # ================== 情感内容检测 ==================
            # 1. 显式情感词汇检测
            emotional_keywords = [
                '不开心', '心情不好', '心情糟糕', '心情差', '难过', '伤心', '郁闷',
                '烦躁', '焦虑', '压力', '累', '疲惫', '累死了', '累死', '疲惫不堪',
                '压抑', '沮丧', '失望', '失落', '孤独', '惆怅', '烦恼', '烦闷'
            ]
            
            has_explicit_emotion = any(keyword in message for keyword in emotional_keywords)
            
            # 2. 基于emotion_profile的压力判断
            has_profile_emotion = emotion_profile.pressure_level > 0 or emotion_profile.energy_level < 5
            
            # 3. 综合情感判断 (显式优先，其次用profile)
            has_emotional_content = has_explicit_emotion or (has_profile_emotion and not self._is_pure_location_query(message))
            
            # ================== 位置查询检测 ==================
            location_keywords = [
                '附近', '周边', '周围', '旁边', '哪儿', '哪里', '什么地方',
                '地铁站', '火车站', '机场', '商圈', '景点', '公园', '商场', '餐厅', '咖啡'
            ]
            
            has_location_query = any(keyword in message for keyword in location_keywords)
            
            # 提取显式地点 - 更精确的匹配
            explicit_locations = [
                '上海火车站', '北京站', '广州南站', '深圳北站', '杭州东站',
                '人民广场', '外滩', '陆家嘴', '徐家汇', '静安寺', '南京路',
                '东方明珠', '豫园', '南京西路', '淮海路', '八佰伴'
            ]
            
            found_location = None
            for location in explicit_locations:
                if location in message:
                    found_location = location
                    break
            
            # ================== 需求类型判定 ==================
            needs_location = has_location_query or found_location
            needs_emotional_support = has_emotional_content
            
            # 优先级：情感 > 混合 > 功能性
            if has_emotional_content and needs_location:
                requirement_type = "mixed"
            elif has_emotional_content:
                requirement_type = "emotional"
            else:
                requirement_type = "functional"
            
            reaction_plan = {
                "has_emotional_content": has_emotional_content,
                "has_location_query": has_location_query,
                "found_explicit_location": found_location,
                "needs_location": needs_location,
                "needs_emotional_support": needs_emotional_support,
                "requirement_type": requirement_type,
                "pressure_level": emotion_profile.pressure_level,
                "energy_level": emotion_profile.energy_level
            }

            logger.info(f"🎯 ReAct分析完成 - 需求类型: {reaction_plan['requirement_type']}, "
                       f"情感内容: {reaction_plan['has_emotional_content']}, "
                       f"位置查询: {reaction_plan['has_location_query']}")

            return reaction_plan

        except Exception as e:
            logger.error(f"🎯 ReAct分析失败: {e}")
            # 降级返回默认计划
            return {
                "has_emotional_content": True,
                "has_location_query": False,
                "found_explicit_location": None,
                "needs_location": False,
                "needs_emotional_support": True,
                "requirement_type": "emotional"
            }
    
    def _is_pure_location_query(self, message: str) -> bool:
        """
        判断是否是纯粹的位置查询（无情感内容）
        """
        pure_location_patterns = [
            r'.*附近.*', r'.*周边.*', r'.*哪里.*', r'.*哪儿.*',
            r'.*什么地方.*', r'.*在哪儿.*', r'.*在那里.*'
        ]
        
        for pattern in pure_location_patterns:
            if re.search(pattern, message) and len(message) < 20:  # 短消息更可能是纯查询
                return True
        return False
    
    def _generate_emotional_care_question(self, message: str, emotion_profile: EmotionProfile) -> str:
        """
        为情感需求用户生成主动关怀的地址询问
        """
        # 基于压力等级调整语气
        if emotion_profile.pressure_level > 0.7:
            # 高压状态 - 更温柔的关怀
            questions = [
                "感受到你现在的压力比较大，找个安静的地方放松一下会很有帮助。你在哪个区域呢？我来为你找找能舒缓心情的地方🌸",
                "理解你现在的疲惫感，换个环境对心情很有帮助。能告诉我在哪个地铁站附近吗？我来帮你找安静的去处🌿",
                "在累的时候确实需要找个舒适的地方休息。你在哪儿呢？我帮你找个能让人放松的地方吧💫",
                "心情不好的时候，找个安静的地方待会儿会好很多。你现在在哪个区域？我来为你物色合适的去处🍃"
            ]
        else:
            # 一般情绪 - 适度关怀
            questions = [
                "听起来你现在状态不太好，要不要我帮你找个安静的地方放松一下？你在哪个区域呢？🌟",
                "感到累的时候确实需要换换心情。你在哪儿呢？我来帮你找找附近有什么治愈的地方～",
                "要不要找个舒适的地方休息一下？能告诉我在哪个地铁站附近吗？我来为你查找～",
                "我理解你现在的感受。你在哪个区域？我帮你找找适合放松心情的地方🌱"
            ]
        
        return random.choice(questions)
    
    def _is_valid_location(self, location: str) -> bool:
        """
        验证提取的地点是否为有效的地理位置
        """
        if not location or len(location) < 2:
            return False
        
        # 过滤常见无效词
        invalid_words = ['商场', '附近', '周边', '周围', '旁边', '边上', '在哪儿', '在那里']
        if any(word in location for word in invalid_words):
            return False
        
        # 验证包含有效地理位置特征
        valid_patterns = [
            r'.*(站|路|街|道|村|镇|乡|区|县|里|弄|巷)',
            r'.*(火车站|地铁站|机场|大桥|公园|广场|大厦|大厦)',
            r'.*(三里屯|西单|王府井|外滩|陆家嘴|徐家汇|静安寺)'
        ]
        
        for pattern in valid_patterns:
            if re.search(pattern, location):
                return True
        
        # 长度检查 (中文地址通常2-8个字符)
        return 2 <= len(location) <= 8

    def _determine_search_params_based_on_react(self, reaction_plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        🎯 ReAct - Stage 4.1: 基于ReAct分析结果确定POI搜索参数
        
        Args:
            reaction_plan: ReAct分析结果
            
        Returns:
            Dict: 搜索参数
        """
        # 基础参数
        params = {
            "radius": 1000,  # 默认1公里
            "limit": 8,      # 默认8个结果
        }
        
        # 🎯 基于情感状态调整搜索策略
        if reaction_plan.get("has_emotional_content"):
            # 情绪问题用户需要更小范围、更近的选择
            if reaction_plan.get("pressure_level", 0) > 0.7:
                # 高压状态 - 500米范围内，少量精选
                params.update({
                    "radius": 500,
                    "limit": 5,
                    "preference": "quiet"  # 偏好安静场所
                })
            else:
                # 一般负面情绪 - 800米范围
                params.update({
                    "radius": 800,
                    "limit": 6,
                    "preference": "healing" # 偏好疗愈场所
                })
        else:
            # 功能需求用户，可以扩大范围
            params.update({
                "radius": 1500,
                "limit": 10,
                "preference": "functional" # 偏好功能性场所
            })
        
        # 🎯 基于需求类型进一步细化
        requirement_type = reaction_plan.get("requirement_type", "functional")
        
        if requirement_type == "emotional":
            # 纯情绪需求，专注放松场所
            params.update({
                "categories": ["cafe", "bookstore", "park", "spa", "meditation"],
                "atmosphere": "quiet_cozy"
            })
        elif requirement_type == "mixed":
            # 混合需求，平衡功能性和疗愈性
            params.update({
                "categories": ["cafe", "bookstore", "movie_theater", "shopping_mall", "restaurant"],
                "atmosphere": "balanced"
            })
        else:
            # 功能性需求，多样化选择
            params.update({
                "categories": ["restaurant", "shopping_mall", "entertainment", "service"],
                "atmosphere": "vibrant"
            })
        
        logger.info(f"🎯 基于ReAct分析确定的搜索参数: {params}")
        return params
        
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
        # 🎯 改进的地址提取策略
        current_location = None
        
        # 优先级1: 显式地点匹配 (来自 ReAct 分析)
        if hasattr(thread_state, '_reaction_plan'):
            found_location = thread_state._reaction_plan.get("found_explicit_location")
            if found_location:
                current_location = found_location
                logger.info(f"🎯 使用 ReAct 检测到的明确地点: {current_location}")
                # 不再提前返回，需要完成后续流程构建完整的返回

        
        # 优先级2: 智能提取附近地点
        smart_patterns = [
            r'([^，。！？]+)附近',      # "上海火车站附近" -> "上海火车站"
            r'([^，。！？]+)周边',      # "陆家嘴周边" -> "陆家嘴"
            r'([^，。！？]+)周围',      # "外滩周围" -> "外滩"
            r'在([^，。！？]+)附近',    # "在上海火车站附近" -> "上海火车站"
            r'([^，。！？]+)(边上|旁边)' # "商场边上" -> "商场"
        ]
        
        for pattern in smart_patterns:
            match = re.search(pattern, message)
            if match:
                extracted = match.group(1).strip()
                # 验证是否为有效地点
                if self._is_valid_location(extracted):
                    current_location = extracted
                    break
        
        # 优先级3: 原patterns (兼容性)
        location_patterns = [
            r'(在|到|去)(.*?)(附近|旁边|楼下|周围)',  # "我在三里屯soho附近"
            r'位于(.*?)(路|街|道|号)',               # "我位于朝阳区东三环中路5号"
            r'(.*?)(路|街|道)[0-9０-９]+号',        # "建国门外大街99号"
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, message)
            if match:
                extracted = match.group(2) if len(match.groups()) > 1 else match.group(1)
                if self._is_valid_location(extracted):
                    current_location = extracted
                    break
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
        # 🎯 ReAct Integration: 存储ReAct分析结果到thread_state
        thread_state._reaction_plan = getattr(thread_state, '_reaction_plan', {})
        
        if current_location and current_location != history_location:
            history_slot = {
                "location": current_location,
                "lat": None,  # 将在分支A中通过Geo API注入
                "lng": None,
                "updated_at": datetime.now().isoformat()
            }
            thread_state.metadata["address_slot"] = history_slot
            logger.info(f"🎯 更新地址槽位: {current_location} (覆盖历史: {history_location})")
        
        # 重新读取更新后的地址槽位
        address_exists = bool(thread_state.metadata.get("address_slot", {}).get("location"))
        if address_exists:
            return {
                "address_exists": True,
                "address_value": thread_state.metadata["address_slot"]["location"],
                "lat": thread_state.metadata["address_slot"].get("lat"),
                "lng": thread_state.metadata["address_slot"].get("lng"),
                "ai_ask_location_sentence": None 
            }
        
        # 🎯 ReAct Integration: 基于ReAct分析结果生成智能询问
        reaction_plan = getattr(thread_state, '_reaction_plan', {})
        
        # 检查用户是否明确提到了地点但没有提取成功
        explicit_locations_backup = ['上海火车站', '北京站', '广州南站', '深圳北站', '杭州东站', '人民广场', '外滩']
        detected_location = None
        for loc in explicit_locations_backup:
            if loc in message:
                detected_location = loc
                break
                
        if detected_location and reaction_plan.get("has_emotional_content"):
            # 用户提到了地点，但由于否定等原因被过滤了，给出智能建议
            return {
                "address_exists": False,
                "address_value": None,
                "lat": None,
                "lng": None,
                "ai_ask_location_sentence": f"我注意到您提到了{detected_location}，您是希望查找这个区域附近的好去处吗？或者其他位置呢？🌿"
            }
        
        # 🎯 ReAct Integration: 基于情感状态和需求类型的智能共情询问
        if reaction_plan.get("has_emotional_content"):
            # 情绪问题为主的询问策略
            if reaction_plan.get("pressure_level", 0) > 0.7:
                # 高压状态 - 更温柔的询问
                location_questions = [
                    "感受到你现在压力比较大，能告诉我在哪个区域吗？我为你找找能放松心情的地方🌱",
                    "理解你的压力，能说说你在哪个地铁站附近吗？我来帮你找安静的角落✨",
                    "在压力大的时候确实需要换个环境，你在哪儿呢？我帮你物色舒适的去处💫",
                    "心情压抑的时候，找个舒适的地方很重要。能告诉我在哪个区域吗？🌸"
                ]
            else:
                # 一般负面情绪 - 适度共情
                location_questions = [
                    "看到你现在心情不太好，很关心你。能告诉我在哪个区域吗？我帮你找治愈的地方～",
                    "感到疲惫的时候确实需要找个安静的地方休息，你在哪儿呢？我来为你查找～",
                    "能理解你现在的感受，你在哪个地铁站附近呢？我来为你寻找合适的去处～",
                    "不论你现在在哪里，我都很关心。告诉我你的位置，我来为你找找好去处～"
                ]
        else:
            # 功能需求为主 - 简洁直接
            location_questions = [
                "你在哪个区域呢？我帮你找找附近的优质选择～",
                "能告诉我你的位置吗？这样我能为你推荐最合适的地方✨",
                "你在哪儿呢？我来帮你搜索附近的好去处🌟"
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
        
        # 🎯 ReAct Stage 1: Thought - 分析复合需求
        # 用户可能同时表达情感和具体需求，需要智能拆解
        reaction_plan = await self._analyze_react_requirements(message, emotion_profile)
        
        # 🎯 ReAct Integration: 将ReAct分析结果传递给thread_state
        thread_state._reaction_plan = reaction_plan
        
        # 🎯 ReAct Stage 2: Action - 尝试获取位置信息  
        address_result = await self._intercept_and_store_address(message, thread_state)
        
        # 🎯 ReAct Stage 3: Observation & Decision
        if not address_result["address_exists"] and reaction_plan["needs_location"]:
            # 分支B: 地址不存在但用户需要位置服务，温柔询问（保护隐私，只问地铁站或区域）
            return {
                "type": "clarification",
                "empathy_response": address_result["ai_ask_location_sentence"],
                "requires_clarification": True,
                "address_query": True,
            }
        
        # 🎯 新增分支: 纯情感需求用户，主动关怀询问位置
        if (not address_result["address_exists"] and 
            reaction_plan["has_emotional_content"] and 
            reaction_plan["requirement_type"] == "emotional"):
            # 分支C: 用户有情绪问题，主动询问是否要找个地方放松
            emotional_care_question = self._generate_emotional_care_question(message, emotion_profile)
            return {
                "type": "emotional_care",
                "empathy_response": emotional_care_question,
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
        if (address_result["lat"] is None or address_result["lng"] is None) and "address_slot" in thread_state.metadata:
            location_coords = await self.booking_execution_tool.get_location_by_query(
                thread_state.metadata["address_slot"]["location"]
            )
            if location_coords:
                thread_state.metadata["address_slot"]["lat"] = location_coords["lat"]
                thread_state.metadata["address_slot"]["lng"] = location_coords["lng"]
                logger.info(f"通过Geo注入位置: {thread_state.metadata['address_slot']['location']} (lat={location_coords['lat']}, lng={location_coords['lng']})")
        
        # 🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕🆕
        # 🎯 ReAct Stage 4: Action - 智能POI搜索（基于用户情绪需求）
        initial_plans = []
        address_slot = thread_state.metadata.get("address_slot", {})
        lat = address_slot.get("lat")
        lng = address_slot.get("lng")
        
        # 🎯 ReAct Integration: 基于用户情绪和需求调整搜索策略
        search_params = self._determine_search_params_based_on_react(reaction_plan)
        
        if lat and lng:
            nearby_pois = await self.booking_execution_tool.route_query_to_pois(
                address_slot["location"],
                radius=search_params["radius"],
                results_limit=search_params["limit"]
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
            vibe_context, message, quest_narrative, enhanced_plans, thread_state
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
        
        # 🎯 序列化处理: 确保所有数据都可JSON序列化
        safe_booking_assessment = None
        if booking_assessment:
            # 深拷贝并确保所有枚举都被转换为字符串
            safe_booking_assessment = booking_assessment.copy()
            if 'risk_level' in safe_booking_assessment and hasattr(safe_booking_assessment['risk_level'], 'value'):
                safe_booking_assessment['risk_level'] = safe_booking_assessment['risk_level'].value
        
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
            "booking_assessment": safe_booking_assessment,
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
        
        merchant_name = getattr(getattr(detailed_scenario, 'merchant', None), 'name', '未知商家')
        logger.info(f"详细方案生成完成 - 商家: {merchant_name}")
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
            # 安全获取商家信息
            if not detailed_scenario or not hasattr(detailed_scenario, 'merchant') or not detailed_scenario.merchant:
                logger.info("实时信息检索：商家对象为None，跳过检索")
                return detailed_scenario
            
            merchant_name = getattr(detailed_scenario.merchant, 'name', '未知商家')
            location_obj = getattr(detailed_scenario.merchant, 'location', None)
            merchant_address = getattr(location_obj, 'address', '未知地址')
            
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
            # 安全检查属性存在性
            if not detailed_scenario or not hasattr(detailed_scenario, 'merchant') or not detailed_scenario.merchant:
                logger.info("预订评估：商家对象不存在或为None")
                return None
                
            merchant_info = {
                'name': getattr(detailed_scenario.merchant, 'name', '未知商家'),
                'address': getattr(getattr(detailed_scenario.merchant, 'location', None), 'address', '未知地址'),
                'type': getattr(getattr(detailed_scenario.merchant, 'type', None), 'value', '未知类型'),
                'contact': getattr(detailed_scenario.merchant, 'contact', '未提供')
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
                                                enhanced_plans: List[Dict] = None,
                                                thread_state = None) -> Any:
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
            # 没有可用商家时，返回特殊标记让LLM生成解释性回复
            from dataclasses import dataclass
            
            @dataclass
            class NoRealTimeDataScenario:
                """实时数据不可用时的特殊场景对象"""
                scenario_type: str = "no_real_time_data"
                user_location: str = ""
                failure_reason: str = ""
                scenario_id: str = "no_real_time_scenario"
                
                # 添加merchant属性以便main.py能正确识别
                @property
                def merchant(self):
                    return None
                
                # 添加enhanced_response属性以触发LLM处理
                @property 
                def enhanced_response(self):
                    return f"很抱歉，我在获取{self.user_location}附近的实时商家信息时遇到了技术问题。让我为您提供一些通用的建议..."
            
            # 创建特殊场景对象
            user_location = "该位置"
            if thread_state and hasattr(thread_state, 'metadata'):
                user_location = thread_state.metadata.get("address_slot", {}).get("location", "该位置")
            
            detailed_scenario = NoRealTimeDataScenario(
                user_location=user_location,
                failure_reason="实时搜索失败或无可用商家"
            )
            logger.info(f"实时商家搜索失败，创建特殊场景对象: {detailed_scenario.user_location}")
        
        logger.info(f"增强详细方案生成完成 - 模式: {scenario_mode}")
        return detailed_scenario
        
    def _select_best_merchant(self, available_plans: List[Dict]) -> Dict:
        """选择最佳商家（评分最高，距离最近）"""
        if not available_plans:
            return None
        
        def score_plan(plan):
            rating = plan.get("rating", 0) or 0
            distance = plan.get("distance", 999) or 999
            
            # 将距离转换为数字（处理字符串格式的距离）
            try:
                if isinstance(distance, str):
                    # 处理带单位的字符串距离（如 "1.5km", "150m"）
                    distance_clean = distance.lower().replace('km', '').replace('m', '').strip()
                    distance = float(distance_clean)
                else:
                    distance = float(distance)
            except (ValueError, TypeError):
                distance = 999.0  # 默认值：较远距离
            
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
