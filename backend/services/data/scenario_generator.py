"""
完整的场景方案生成器 - 高德地图POI数据源适配版本
整合高德地图POI搜索结果和路径规划，生成完整细致的出游方案
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional, Union
import random
import json
import logging
from datetime import datetime, timedelta
import hashlib

# 导入高德地图相关的数据结构
from ..tools.booking_execution_tool import (
    AmapPoiResult, AmapRouteResult, AmapExecutionTool
)
from .merchant_database import (
    Merchant, MerchantType, COFFEE_SHOPS, 
    RESTAURANTS, PARK_LANDSCAPES, BOOKSTORES,
    get_random_merchant, search_merchants_by_features
)
from .route_generator import CompleteScenarioGenerator, DetailedRoute
from .data_anchor_enhancer import DataAnchorEnhancer, AnchorPoint


@dataclass
class WeatherInfo:
    """天气信息"""
    condition: str  # sunny, cloudy, rainy, hot, cold
    temperature: int  # 摄氏度
    description: str
    recommendation: str


@dataclass
class CostBreakdown:
    """费用明细"""
    transportation: float
    consumption: float
    activities: float
    emergency_reserve: float
    total: float


@dataclass
class NearbyRecommendation:
    """附近推荐"""
    name: str
    type: str
    distance: float  # 米
    description: str
    emergency: bool = False


@dataclass 
class SafetyInfo:
    """安全信息"""
    area_safety: str
    emergency_contacts: List[str]
    safety_tips: List[str]
    medical_facilities: List[str]


@dataclass
class AmapScenario:
    """高德版方案数据类"""
    scenario_id: str
    title: str
    poi_info: AmapPoiResult  # 高德POI数据
    route_info: AmapRouteResult  # 高德路径数据
    weather: WeatherInfo
    cost_breakdown: CostBreakdown
    detailed_itinerary: List[Dict[str, Any]]
    nearby_recommendations: List[NearbyRecommendation]
    safety_info: SafetyInfo
    personalization_notes: Dict[str, str]
    backup_options: List[Dict[str, Any]]


@dataclass
class CompleteScenario:
    """完整出游方案"""
    scenario_id: str
    title: str
    merchant: Merchant
    route: DetailedRoute
    weather: WeatherInfo
    cost_breakdown: CostBreakdown
    detailed_itinerary: List[Dict[str, Any]]
    nearby_recommendations: List[NearbyRecommendation]
    safety_info: SafetyInfo
    personalization_notes: Dict[str, str]
    backup_options: List[Dict[str, Any]]


class EnhancedScenarioGenerator:
    """
    增强版场景生成器 - 高德地图POI数据适配版本
    支持传统合成数据和高德API数据的统一处理
    """
    
    def __init__(self):
        self.scenario_generator = CompleteScenarioGenerator()
        self.weather_conditions = {
            "sunny": ["晴天", "气温宜人，阳光充足", "记得防晒，多补充水分"],
            "cloudy": ["多云", "天气舒适，适合出门", "温差较小，穿衣方便"],
            "rainy": ["小雨", "阴雨天气，湿度较高", "请带伞，选择室内活动"],
            "hot": ["炎热", "气温偏高", "选择有空调的场所，注意防暑"],
            "cold": ["寒冷", "气温偏低", "注意保暖，选择温暖场所"]
        }
        
        # 高德地图执行工具（用于实时数据查询）
        self.amap_tool = None
        
        # 数据锚点增强器（解决同名店铺混淆）
        self.anchor_enhancer = DataAnchorEnhancer()
        
    def _convert_amap_to_merchant(self, amap_poi: AmapPoiResult) -> Merchant:
        """将高德POI数据转换为Merchant对象"""
        # 解析坐标
        try:
            lng, lat = amap_poi.location.split(',')
            lng, lat = float(lng), float(lat)
        except (ValueError, AttributeError):
            lng, lat = 116.397470, 39.908823  # 默认位置
        
        # 确定商家类型
        poi_type_mapping = {
            "05": MerchantType.COFFEE_SHOP,  # 餐饮相关
            "06": MerchantType.RESTAURANT,   # 购物相关  
            "08": MerchantType.BOOKSTORE,    # 文化相关
            "10": MerchantType.PARK,         # 公共设施
        }
        
        merchant_type = MerchantType.COFFEE_SHOP  # 默认
        if amap_poi.typecode:
            type_prefix = amap_poi.typecode[:2]
            merchant_type = poi_type_mapping.get(type_prefix, MerchantType.COFFEE_SHOP)
        
        # 解析距离
        try:
            distance = float(amap_poi.distance) if amap_poi.distance else 1000
        except (ValueError, TypeError):
            distance = 1000
        
        # 创建Location对象
        from .merchant_database import Location
        location = Location(
            address=amap_poi.address,
            city="北京",  # 可从POI数据中提取
            area=amap_poi.business_area or "附近商圈",
            latitude=lat,
            longitude=lng
        )
        
        # 生成基础特征
        features = self._extract_features_from_poi(amap_poi)
        
        # 创建Merchant对象
        merchant = Merchant(
            id=amap_poi.id or f"amap_{hashlib.md5(amap_poi.name.encode()).hexdigest()[:8]}",
            name=amap_poi.name,
            type=merchant_type,
            location=location,
            rating=float(amap_poi.rating) if amap_poi.rating else 4.5,
            price_level=self._get_price_level(amap_poi.cost),
            features=features,
            contact=amap_poi.tel,
            operating_hours=self._generate_operating_hours(),
            solo_friendly=True,  # 高德数据默认友好
            distance=distance,
            menu=self._generate_sample_menu(merchant_type),
            packages=self._generate_sample_packages(merchant_type)
        )
        
        return merchant
    
    def _convert_amap_to_route(self, amap_route: AmapRouteResult, 
                              start_location: str = None) -> DetailedRoute:
        """将高德路径数据转换为DetailedRoute对象"""
        from .route_generator import (
            DetailedRoute, RouteSegment, TransportOption, 
            TimeSlot, TransportType
        )
        
        try:
            distance_km = float(amap_route.distance) / 1000 if amap_route.distance else 0
            duration_minutes = float(amap_route.duration) / 60 if amap_route.duration else 0
        except (ValueError, TypeError):
            distance_km = 0
            duration_minutes = 0
        
        # 确定交通方式
        transport_type = TransportType.TRANSIT  # 默认
        transport_desc = "智能推荐路线"
        
        # 根据费用判断交通方式
        if amap_route.taxi_cost and float(amap_route.taxi_cost) > 0:
            transport_type = TransportType.DRIVING
            transport_desc = "驾车出行"
        
        # 创建交通选项
        transport = TransportOption(
            type=transport_type,
            description=transport_desc,
            duration=int(duration_minutes),
            cost=round(float(amap_route.taxi_cost or 0), 2),
            carbon_footprint=round(distance_km * 0.21, 2),  # 估算碳排放
            comfort_level=4 if transport_type == TransportType.DRIVING else 3
        )
        
        # 创建时间槽
        current_time = datetime.now()
        time_slot = TimeSlot(
            start_time=0,
            end_time=int(duration_minutes),
            description="前往目的地",
            efficiency=0.9
        )
        
        # 创建路由段
        route_segment = RouteSegment(
            from_location=start_location or "出发地",
            to_location="目的地",
            distance=distance_km,
            transport=transport,
            time_breakdown=[time_slot],
            instructions=self._parse_amap_steps(amap_route.steps),
            alternatives=[]
        )
        
        # 创建完整路线
        route = DetailedRoute(
            route_segments=[route_segment],
            total_distance=distance_km,
            total_duration=int(duration_minutes),
            total_cost=transport.cost,
            carbon_savings=max(0, 5.0 - transport.carbon_footprint),  # 估算碳节约
            time_schedule=[time_slot],
            optimization_tips=self._get_route_tips(distance_km, duration_minutes)
        )
        
        return route
    
    def _extract_features_from_poi(self, amap_poi: AmapPoiResult) -> List[str]:
        """从高德POI提取场所特征"""
        base_features = []
        
        # 根据POI类型添加特征
        if "咖啡" in amap_poi.type or "0501" in amap_poi.typecode:
            base_features.extend(["咖啡香浓", "环境安静", "适合独处", "轻音乐"])
        elif "餐厅" in amap_poi.type or "0502" in amap_poi.typecode:
            base_features.extend(["美食丰富", "服务态度好", "用餐环境", "性价比高"])
        elif "书店" in amap_poi.type or "0802" in amap_poi.typecode:
            base_features.extend(["图书丰富", "阅读环境", "文艺氛围", "安静角落"])
        elif "公园" in amap_poi.type or "1001" in amap_poi.typecode:
            base_features.extend(["自然风光", "空气清新", "散步好去处", "休闲放松"])
        
        # 如果没有匹配到特定类型，添加通用特征
        if not base_features:
            base_features = ["环境优美", "适合休闲", "交通便利", "服务态度好"]
        
        return base_features
    
    def _get_price_level(self, cost_str: str) -> int:
        """根据费用字符串确定价格等级"""
        try:
            cost = float(cost_str)
            if cost < 30:
                return 1  # 经济型
            elif cost < 80:
                return 2  # 中等
            else:
                return 3  # 高端
        except (ValueError, TypeError):
            return 2  # 默认中等
    
    def _generate_operating_hours(self):
        """生成营业时间"""
        from .merchant_database import OperatingHours
        return OperatingHours(
            monday="09:00-22:00",
            tuesday="09:00-22:00", 
            wednesday="09:00-22:00",
            thursday="09:00-22:00",
            friday="09:00-22:00",
            saturday="09:00-22:00",
            sunday="09:00-22:00"
        )
    
    def _generate_sample_menu(self, merchant_type: MerchantType):
        """生成示例菜单"""
        from .merchant_database import MenuItem
        
        if merchant_type == MerchantType.COFFEE_SHOP:
            return [
                MenuItem(name="手冲单品咖啡", description="精选单品豆，现磨现冲", price=35.0),
                MenuItem(name="经典美式", description="浓郁香醇，唤醒活力", price=22.0)
            ]
        elif merchant_type == MerchantType.RESTAURANT:
            return [
                MenuItem(name="招牌套餐", description="精选主菜+汤品+小菜", price=68.0),
                MenuItem(name="轻食沙拉", description="新鲜蔬菜，健康首选", price=32.0)
            ]
        else:
            return []
    
    def _generate_sample_packages(self, merchant_type: MerchantType):
        """生成示例套餐"""
        from .merchant_database import PackageDeal
        
        if merchant_type == MerchantType.COFFEE_SHOP:
            return [
                PackageDeal(
                    name="午后悠闲套餐",
                    items=["咖啡+甜点"],
                    original_price=58.0,
                    discounted_price=48.0,
                    description="享受慢时光的完美组合"
                )
            ]
        else:
            return []
    
    def _parse_amap_steps(self, steps: List[Dict[str, Any]]) -> List[str]:
        """解析高德路径规划步骤"""
        if not steps:
            return ["按照导航前行"]
        
        instructions = []
        for step in steps:
            instruction = step.get("instruction", "")
            if instruction:
                # 清理高德返回的HTML标签
                import re
                clean_instruction = re.sub(r'<[^>]+>', '', instruction)
                instructions.append(clean_instruction)
        
        if not instructions:
            instructions = ["按照导航提示前往目的地"]
        
        return instructions
    
    def _get_route_tips(self, distance: float, duration: float) -> List[str]:
        """生成路线优化建议"""
        tips = []
        
        if duration > 60:
            tips.append("建议选择公共交通工具，更省时便捷")
        
        if distance < 2:
            tips.append("距离较近，步行是个不错的选择")
        
        if distance > 10:
            tips.append("距离较远，建议预留充足时间")
        
        tips.append("路上注意安全，保持好心情")
        
        return tips
    
    def generate_weather_info(self) -> WeatherInfo:
        """生成天气信息"""
        condition = random.choice(list(self.weather_conditions.keys()))
        condition_data = self.weather_conditions[condition]
        
        # 根据天气设定合理温度
        temp_ranges = {
            "sunny": (18, 25),
            "cloudy": (16, 22),
            "rainy": (14, 20),
            "hot": (28, 35),
            "cold": (2, 10)
        }
        
        min_temp, max_temp = temp_ranges.get(condition, (18, 25))
        temperature = random.randint(min_temp, max_temp)
        
        return WeatherInfo(
            condition=condition,
            temperature=temperature,
            description=condition_data[0] + "，" + condition_data[1],
            recommendation=condition_data[2]
        )
    
    def generate_cost_breakdown(self, route: DetailedRoute, merchant: Merchant) -> CostBreakdown:
        """生成详细费用明细"""
        # 交通费用
        transportation_cost = route.total_cost * 0.3  # 假设交通占30%
        
        # 消费费用
        if merchant.type == MerchantType.COFFEE_SHOP:
            consumption_cost = random.uniform(25, 50)
        elif merchant.type == MerchantType.RESTAURANT:
            consumption_cost = random.uniform(40, 80)
        elif merchant.type == MerchantType.BOOKSTORE:
            consumption_cost = random.uniform(0, 100)  # 可能不买书
        else:
            consumption_cost = 0  # 公园免费
        
        # 活动费用
        activities_cost = random.uniform(0, 20)  # 一些小消费
        
        # 应急储备金
        emergency_reserve = 50  # 建议携带的应急资金
        
        total = transportation_cost + consumption_cost + activities_cost
        
        return CostBreakdown(
            transportation=round(transportation_cost, 2),
            consumption=round(consumption_cost, 2),
            activities=round(activities_cost, 2),
            emergency_reserve=emergency_reserve,
            total=round(total, 2)
        )
    
    def generate_detailed_itinerary(self, 
                                  merchant: Merchant, 
                                  route: DetailedRoute,
                                  weather: WeatherInfo) -> List[Dict[str, Any]]:
        """生成详细时间表"""
        current_time = datetime.now()
        itinerary = []
        
        # 出发准备阶段
        itinerary.append({
            "time": current_time.strftime("%H:%M"),
            "title": "⏰ 出发准备",
            "location": "家",
            "duration": 15,
            "description": "洗漱整理，检查随身物品",
            "checklist": [
                "手机充电器",
                "钱包",
                "身份证",
                "水杯"
            ],
            "weather_notes": f"当前{weather.condition}，建议{weather.recommendation}"
        })
        
        # 交通出行阶段
        travel_end_time = current_time + timedelta(minutes=route.time_schedule[0].end_time if route.time_schedule else 30)
        itinerary.append({
            "time": (current_time + timedelta(minutes=15)).strftime("%H:%M"),
            "title": "🚶‍♀️ 前往目的地",
            "location": "在途中",
            "duration": int(route.total_duration * 0.2),
            "description": f"{route.route_segments[0].transport.description}前往{merchant.name}",
            "notes": f"距离约{route.total_distance}公里，预计花费{route.route_segments[0].transport.duration}分钟",
            "cost": f"¥{route.route_segments[0].transport.cost:.2f}"
        })
        
        # 到达目的地阶段
        arrival_time = travel_end_time
        if merchant.type in [MerchantType.COFFEE_SHOP, MerchantType.RESTAURANT]:
            # 餐饮场所活动安排
            itinerary.extend([
                {
                    "time": arrival_time.strftime("%H:%M"),
                    "title": "🏪 到达目的地",
                    "location": merchant.location.address,
                    "duration": 5,
                    "description": f"进入{merchant.name}，寻找合适座位",
                    "notes": "选择安静角落，观察环境"
                },
                {
                    "time": (arrival_time + timedelta(minutes=5)).strftime("%H:%M"),
                    "title": "📋 点单时间",
                    "location": merchant.name,
                    "duration": 15,
                    "description": "浏览菜单，选择喜欢的饮品或食物",
                    "recommendation": self._get_menu_recommendation(merchant),
                    "decision_help": self._get_decision_help(merchant)
                },
                {
                    "time": (arrival_time + timedelta(minutes=20)).strftime("%H:%M"),
                    "title": "☕ 享受时光",
                    "location": merchant.name,
                    "duration": int(route.total_duration * 0.6),
                    "description": "慢慢品味，享受独处时光",
                    "activities": [
                        "静心品尝",
                        "观察周围",
                        "写下感受",
                        "深呼吸放松"
                    ],
                    "environmental_notes": f"店内环境：{', '.join(merchant.features[:3])}"
                },
                {
                    "time": (arrival_time + timedelta(minutes=route.total_duration - 10)).strftime("%H:%M"),
                    "title": "📝 记录感受",
                    "location": merchant.name,
                    "duration": 10,
                    "description": "记录这次体验的感受和想法",
                    "prompts": [
                        "今天的感受如何？",
                        "环境给你什么感觉？",
                        "味道怎么样？",
                        "下次还想来吗？"
                    ]
                }
            ])
        
        elif merchant.type == MerchantType.PARK:
            # 公园活动安排
            itinerary.extend([
                {
                    "time": arrival_time.strftime("%H:%M"),
                    "title": "🌳 进入公园",
                    "location": merchant.location.address,
                    "duration": 5,
                    "description": "走进公园，感受自然环境",
                    "notes": "选择一条喜欢的路线开始漫步"
                },
                {
                    "time": (arrival_time + timedelta(minutes=5)).strftime("%H:%M"),
                    "title": "🚶‍♀️ 公园漫步",
                    "location": f"{merchant.name}园区内",
                    "duration": int(route.total_duration * 0.7),
                    "description": "慢步游走，观察自然景观",
                    "route_options": [
                        "湖边步道",
                        "林荫小径",
                        "花园区",
                        "草坪区域"
                    ],
                    "activities": [
                        "拍照留念",
                        "观察动植物",
                        "深呼吸练习",
                        "静坐观湖"
                    ]
                },
                {
                    "time": (arrival_time + timedelta(minutes=route.total_duration - 10)).strftime("%H:%M"),
                    "title": "☕ 休息时刻",
                    "location": f"{merchant.name}休息区",
                    "duration": 10,
                    "description": "在休息区稍作休息",
                    "notes": "喝水补充体力，观察周围景色"
                }
            ])
        
        elif merchant.type == MerchantType.BOOKSTORE:
            # 书店活动安排
            itinerary.extend([
                {
                    "time": arrival_time.strftime("%H:%M"),
                    "title": "📚 进入书店",
                    "location": merchant.location.address,
                    "duration": 5,
                    "description": "走进书店，寻找感兴趣的书",
                    "notes": "保持安静，尊重阅读环境"
                },
                {
                    "time": (arrival_time + timedelta(minutes=5)).strftime("%H:%M"),
                    "title": "🔍 浏览书籍",
                    "location": merchant.name,
                    "duration": int(route.total_duration * 0.5),
                    "description": "在各个书架间浏览，寻找喜欢的书",
                    "section_recommendations": [
                        "文学小说区",
                        "生活美学区",
                        "心灵成长区",
                        "艺术文化区"
                    ]
                },
                {
                    "time": (arrival_time + timedelta(minutes=route.total_duration * 0.55)).strftime("%H:%M"),
                    "title": "📖 深度阅读",
                    "location": merchant.name,
                    "duration": int(route.total_duration * 0.35),
                    "description": "找到合适的书，开始阅读",
                    "reading_tips": [
                        "选择安静角落",
                        "调节好坐姿",
                        "沉浸于书中世界",
                        "记录喜欢的段落"
                    ]
                }
            ])
        
        # 返回准备
        itinerary.append({
            "time": (arrival_time + timedelta(minutes=route.total_duration)).strftime("%H:%M"),
            "title": "🏠 准备返程",
            "location": merchant.name,
            "duration": 5,
            "description": "整理物品，准备返程",
            "checklist": [
                "手机",
                "钱包", 
                "购买的书或商品",
                "不要遗忘任何物品"
            ]
        })
        
        return itinerary
    
    def _get_menu_recommendation(self, merchant: Merchant) -> str:
        """获取菜单推荐"""
        if not merchant.menu:
            return "店家会根据您的喜好推荐合适的饮品"
        
        best_sellers = ["手冲单品咖啡", "经典美式", "招牌糕点"]
        for item in merchant.menu:
            if any(best in item.name for best in best_sellers):
                return f"推荐：{item.name} - {item.description} (¥{item.price})"
        
        # 如果没有找到招牌，推荐第一个
        first_item = merchant.menu[0]
        return f"推荐：{first_item.name} - {first_item.description} (¥{first_item.price})"
    
    def _get_decision_help(self, merchant: Merchant) -> str:
        """获取选择建议"""
        if merchant.type == MerchantType.COFFEE_SHOP:
            return "建议选择手冲单品咖啡，口味更加纯正，适合慢慢品味"
        elif merchant.type == MerchantType.RESTAURANT:
            return "可以选择套餐，性价比更高，口味也更加丰富"
        return "跟随自己的喜好，不用考虑太多，享受选择的过程"
    
    def generate_nearby_recommendations(self, merchant: Merchant) -> List[NearbyRecommendation]:
        """生成周边推荐"""
        nearby_places = [
            {
                "name": "全家便利店",
                "type": "便利店",
                "distance": 200,
                "description": "可以补充零食饮料，价格便民",
                "emergency": True
            },
            {
                "name": "中国银行ATM",
                "type": "银行", 
                "distance": 350,
                "description": "自助取款机，24小时服务",
                "emergency": True
            },
            {
                "name": "社区卫生服务站",
                "type": "医疗",
                "distance": 500,
                "description": "基础医疗服务，应急处理",
                "emergency": True
            },
            {
                "name": "地铁{}站".format(merchant.location.area[:2]),
                "type": "交通",
                "distance": 600,
                "description": "返回市中心的便捷交通",
                "emergency": False
            },
            {
                "name": "特色小吃店",
                "type": "餐饮",
                "distance": 400,
                "description": "当地特色小吃，值得一试",
                "emergency": False
            }
        ]
        
        return [NearbyRecommendation(**place) for place in nearby_places]
    
    def generate_safety_info(self, merchant: Merchant) -> SafetyInfo:
        """生成安全信息"""
        safety_levels = ["非常安全", "比较安全", "一般安全"]
        
        area_safety = random.choice(safety_levels)
        
        emergency_contacts = [
            f"{merchant.name}: {merchant.contact}",
            "紧急救援: 110",
            "医疗急救: 120",
            "消防: 119"
        ]
        
        safety_tips = [
            "保持手机电量充足",
            "避免在人少的地方停留过久", 
            "随身携带身份证明",
            "注意保管个人物品"
        ]
        
        medical_facilities = [
            "附近社区卫生中心",
            "{}医院".format(merchant.location.area),
            "24小时药店"
        ]
        
        return SafetyInfo(
            area_safety=area_safety,
            emergency_contacts=emergency_contacts,
            safety_tips=safety_tips,
            medical_facilities=medical_facilities
        )
    
    def generate_backup_options(self, merchant: Merchant) -> List[Dict[str, Any]]:
        """生成备选方案"""
        alternatives = []
        
        # 同类型备选
        same_type_merchants = [
            m for m in search_merchants_by_features([])
            if m.type == merchant.type and m.id != merchant.id
        ]
        
        for i, alt_merchant in enumerate(same_type_merchants[:2]):
            alternatives.append({
                "option_id": f"backup_{i+1}",
                "title": f"备选{i+1}: {alt_merchant.name}",
                "description": f"如果{merchant.name}人满为患，可前往此处",
                "merchant_name": alt_merchant.name,
                "location": alt_merchant.location.address,
                "features": alt_merchant.features[:3],
                "reason": "同类型选择，体验相似"
            })
        
        # 附近同类备选
        nearby_same_type = [
            {
                "option_id": f"nearby_{i+1}",
                "title": f"附近{i+1}: {merchant.location.area}其他选择",
                "description": "同一区域内的其他选择",
                "area": merchant.location.area,
                "features": ["同一区域", "距离较近", "可以调整路线"],
                "reason": "地理位置便利"
            } for i in range(2)
        ]
        
        alternatives.extend(nearby_same_type)
        
        return alternatives
    
    def generate_complete_enhanced_scenario(self, 
                                          user_message: str, 
                                          vibe_mode: str = "healing",
                                          amap_poi: AmapPoiResult = None,
                                          amap_route: AmapRouteResult = None) -> CompleteScenario:
        """生成完整的增强版出游方案 - 支持高德数据和传统数据源"""
        
        # 数据源选择逻辑
        if amap_poi and amap_route:
            # 使用高德实时数据
            logging.info(f"使用高德POI数据生成方案: {amap_poi.name}")
            merchant = self._convert_amap_to_merchant(amap_poi)
            route = self._convert_amap_to_route(amap_route, "当前位置")
        else:
            # 使用传统合成数据
            if vibe_mode == "exploration":
                base_scenario = self.scenario_generator.generate_exploration_scenario(user_message)
            else:
                base_scenario = self.scenario_generator.generate_healing_scenario(user_message)
            
            merchant = base_scenario["merchant"]
            route = base_scenario["route"]
        
        # 生成各类详细数据
        weather = self.generate_weather_info()
        cost_breakdown = self.generate_cost_breakdown(route, merchant)
        detailed_itinerary = self.generate_detailed_itinerary(merchant, route, weather)
        nearby_recommendations = self.generate_nearby_recommendations(merchant)
        safety_info = self.generate_safety_info(merchant)
        backup_options = self.generate_backup_options(merchant)
        
        # 个性化提示
        personalization_notes = {
            "best_visit_time": self._get_best_visit_time(merchant, weather),
            "mood_boosting_tips": self._get_mood_tips(merchant, user_message),
            "photography_spots": self._get_photography_suggestions(merchant),
            "social_distance_advice": "选择角落位置，享受独处时光" if merchant.solo_friendly else "可适当选择人少时段"
        }
        
        # 生成唯一ID
        scenario_id = f"scenario-{datetime.now().strftime('%Y%m%d%H%M%S')}-{random.randint(1000, 9999)}"
        
        return CompleteScenario(
            scenario_id=scenario_id,
            title=f"{merchant.name} - {base_scenario['type']}",
            merchant=merchant,
            route=route,
            weather=weather,
            cost_breakdown=cost_breakdown,
            detailed_itinerary=detailed_itinerary,
            nearby_recommendations=nearby_recommendations,
            safety_info=safety_info,
            personalization_notes=personalization_notes,
            backup_options=backup_options
        )
    
    def _get_best_visit_time(self, merchant: Merchant, weather: WeatherInfo) -> str:
        """获取最佳访问时间建议"""
        if weather.condition in ["hot", "cold"]:
            return "建议选择室内环境，避开极端天气时段"
        
        if merchant.type == MerchantType.PARK:
            best_times = ["清晨(8-10点)", "傍晚(17-19点)"]
            return f"最佳时间：{random.choice(best_times)}，避开正午强光"
        
        if merchant.type in [MerchantType.COFFEE_SHOP, MerchantType.BOOKSTORE]:
            return "下午2-4点是最佳时间，光线舒适，人流量适中"
        
        return "任何时间都适合，根据你的心情决定"
    
    # ==================== 高德地图专用方案生成方法 ==================== #
    
    async def generate_amap_enhanced_scenario(self,
                                             amap_poi: AmapPoiResult,
                                             amap_route: AmapRouteResult,
                                             user_message: str,
                                             vibe_mode: str = "healing") -> AmapScenario:
        """生成高德地图专用版出游方案
        
        Args:
            amap_poi: 高德地图POI搜索结果
            amap_route: 高德地图路径规划结果  
            user_message: 用户原始需求信息
            vibe_mode: 氛围模式(healing/exploration)
            
        Returns:
            AmapScenario: 高德版完整场景方案
        """
        logging.info(f"生成高德专用方案: {amap_poi.name} - {amap_poi.type}")
        
        # 直接使用高德数据生成方案
        scenario_id = f"amap-{datetime.now().strftime('%Y%m%d%H%M%S')}-{hashlib.md5(amap_poi.id.encode()).hexdigest()[:8]}"
        
        title = f"{amap_poi.name} - {self._get_scenario_type(amap_poi, vibe_mode)}"
        
        # 生成各类详细数据
        weather = self.generate_weather_info()
        
        # 创建Merchant对象用于数据生成
        merchant = self._convert_amap_to_merchant(amap_poi)
        route = self._convert_amap_to_route(amap_route, "当前位置")
        
        # 创建数据锚点并进行校验
        try:
            anchor_point = await self.anchor_enhancer.create_anchor_from_poi(amap_poi)
        except Exception as e:
            logging.warning(f"数据锚点创建失败，使用基础模式: {e}")
            anchor_point = None
        if anchor_point:
            verification_info = {
                'anchor_id': anchor_point.unique_id,
                'confidence': anchor_point.confidence,
                'business_area_verified': anchor_point.business_area,
                'coordinates_locked': anchor_point.coordinate,
                'brand_identified': anchor_point.brand_name if anchor_point.brand_name else "N/A"
            }
        else:
            verification_info = {
                'anchor_id': 'unknown',
                'confidence': 0.5,
                'business_area_verified': amap_poi.business_area,
                'coordinates_locked': amap_poi.location,
                'brand_identified': 'unknown'
            }
        
        cost_breakdown = self.generate_cost_breakdown(route, merchant)
        detailed_itinerary = self.generate_detailed_itinerary(merchant, route, weather)
        nearby_recommendations = self.generate_nearby_recommendations(merchant)
        safety_info = self.generate_safety_info(merchant)
        backup_options = self.generate_backup_options(merchant)
        
        personalization_notes = {
            "best_visit_time": self._get_best_visit_time(merchant, weather),
            "mood_boosting_tips": self._get_mood_tips(merchant, user_message),
            "photography_spots": self._get_photography_suggestions(merchant),
            "social_distance_advice": "选择角落位置，享受独处时光" if merchant.solo_friendly else "可适当选择人少时段",
            "amap_specific_notes": f"高德评分: {amap_poi.rating} | 距离: {amap_poi.distance}m | 商圈: {amap_poi.business_area}"
        }
        
        return AmapScenario(
            scenario_id=scenario_id,
            title=title,
            poi_info=amap_poi,
            route_info=amap_route,
            weather=weather,
            cost_breakdown=cost_breakdown,
            detailed_itinerary=detailed_itinerary,
            nearby_recommendations=nearby_recommendations,
            safety_info=safety_info,
            personalization_notes=personalization_notes,
            backup_options=backup_options
        )
    
    def _get_scenario_type(self, amap_poi: AmapPoiResult, vibe_mode: str) -> str:
        """根据高德POI数据和氛围模式确定场景类型"""
        if "咖啡" in amap_poi.type or "0501" in amap_poi.typecode:
            return "咖啡治愈" if vibe_mode == "healing" else "咖啡探索"
        elif "餐厅" in amap_poi.type or "0502" in amap_poi.typecode:
            return "美食治愈" if vibe_mode == "healing" else "美食品鉴"
        elif "书店" in amap_poi.type or "0802" in amap_poi.typecode:
            return "阅读时光" if vibe_mode == "healing" else "文化探索"
        elif "公园" in amap_poi.type or "1001" in amap_poi.typecode:
            return "自然治愈" if vibe_mode == "healing" else "城市漫步"
        else:
            return "休闲治愈" if vibe_mode == "healing" else "城市探索"
    
    def convert_amap_scenario_to_traditional(self, amap_scenario: AmapScenario) -> CompleteScenario:
        """将高德方案转换为传统方案格式以保持兼容性
        
        Args:
            amap_scenario: 高德专用方案
            
        Returns:
            CompleteScenario: 传统格式方案
        """
        # 转换数据格式
        merchant = self._convert_amap_to_merchant(amap_scenario.poi_info)
        route = self._convert_amap_to_route(amap_scenario.route_info, "当前位置")
        
        return CompleteScenario(
            scenario_id=amap_scenario.scenario_id,
            title=amap_scenario.title,
            merchant=merchant,
            route=route,
            weather=amap_scenario.weather,
            cost_breakdown=amap_scenario.cost_breakdown,
            detailed_itinerary=amap_scenario.detailed_itinerary,
            nearby_recommendations=amap_scenario.nearby_recommendations,
            safety_info=amap_scenario.safety_info,
            personalization_notes=amap_scenario.personalization_notes,
            backup_options=amap_scenario.backup_options
        )
    
    def convert_to_unified_api_format(self, scenario: Union[CompleteScenario, AmapScenario]) -> Dict[str, Any]:
        """统一API输出格式 - 支持两种数据源
        
        Args:
            scenario: 方案对象（传统或高德格式）
            
        Returns:
            Dict: 统一的API输出格式
        """
        if isinstance(scenario, AmapScenario):
            # 高德方案数据
            return self._convert_amap_scenario_to_api_format(scenario)
        else:
            # 传统方案数据
            return self.convert_to_api_format(scenario)
    
    def _convert_amap_scenario_to_api_format(self, scenario: AmapScenario) -> Dict[str, Any]:
        """高德方案转API格式"""
        return {
            "scenario_id": scenario.scenario_id,
            "title": scenario.title,
            "poi_info": {
                "id": scenario.poi_info.id,
                "name": scenario.poi_info.name,
                "address": scenario.poi_info.address,
                "location": scenario.poi_info.location,
                "type": scenario.poi_info.type,
                "typecode": scenario.poi_info.typecode,
                "distance": scenario.poi_info.distance,
                "rating": scenario.poi_info.rating,
                "cost": scenario.poi_info.cost,
                "business_area": scenario.poi_info.business_area,
                "photos": scenario.poi_info.photos
            },
            "route_info": {
                "distance": scenario.route_info.distance,
                "duration": scenario.route_info.duration,
                "taxi_cost": scenario.route_info.taxi_cost,
                "steps_count": len(scenario.route_info.steps)
            },
            "cost_breakdown": asdict(scenario.cost_breakdown),
            "weather": {
                "condition": scenario.weather.condition,
                "temperature": f"{scenario.weather.temperature}°C",
                "recommendation": scenario.weather.recommendation
            },
            "detailed_itinerary": scenario.detailed_itinerary,
            "nearby_recommendations": [asdict(r) for r in scenario.nearby_recommendations],
            "safety_info": asdict(scenario.safety_info),
            "personalization_notes": scenario.personalization_notes,
            "backup_options": scenario.backup_options,
            "data_source": "amap_real_time",
            "generated_at": datetime.now().isoformat()
        }
    
    def _get_mood_tips(self, merchant: Merchant, user_message: str) -> str:
        """获取心情提升建议"""
        tips = {
            MerchantType.COFFEE_SHOP: "闭眼闻咖啡香，专注口味层次，感受当下的宁静",
            MerchantType.PARK: "深呼吸新鲜空气，观察树叶轻摇，让自然治愈心灵",
            MerchantType.BOOKSTORE: "让文字带你远离烦恼，探索不同的世界和观点",
            MerchantType.RESTAURANT: "慢慢品味食物的美好，感受舌尖的幸福时刻"
        }
        
        return tips.get(merchant.type, "专注于当下，享受独处的珍贵时光")
    
    def _get_photography_suggestions(self, merchant: Merchant) -> str:
        """获取摄影建议"""
        suggestions = {
            MerchantType.COFFEE_SHOP: "拍摄咖啡拉花、店内环境细节，记录美好瞬间",
            MerchantType.PARK: "拍摄自然风光、光影变化，收藏城市绿洲",
            MerchantType.BOOKSTORE: "拍摄书架排列、阅读角落，展现文艺气氛",
            MerchantType.RESTAURANT: "拍摄食物摆盘、环境氛围，记录美食体验"
        }
        
        return suggestions.get(merchant.type, "用镜头记录下此刻的美好")
    
    def convert_to_api_format(self, scenario: CompleteScenario) -> Dict[str, Any]:
        """转换为API输出格式"""
        return {
            "scenario_id": scenario.scenario_id,
            "title": scenario.title,
            "merchant_info": {
                "name": scenario.merchant.name,
                "type": scenario.merchant.type.value,
                "address": scenario.merchant.location.address,
                "rating": scenario.merchant.rating,
                "features": scenario.merchant.features,
                "price_level": "¥" * scenario.merchant.price_level,
                "solo_friendly": scenario.merchant.solo_friendly,
                "location": {
                    "latitude": scenario.merchant.location.latitude,
                    "longitude": scenario.merchant.location.longitude,
                    "city": scenario.merchant.location.city,
                    "area": scenario.merchant.location.area
                }
            },
            "route_summary": {
                "distance": f"{scenario.route.total_distance}公里",
                "duration": f"{scenario.route.total_duration}分钟",
                "transport": scenario.route.route_segments[0].transport.description,
                "total_cost": f"¥{scenario.route.total_cost:.2f}"
            },
            "cost_breakdown": asdict(scenario.cost_breakdown),
            "weather": {
                "condition": scenario.weather.condition,
                "temperature": f"{scenario.weather.temperature}°C",
                "recommendation": scenario.weather.recommendation
            },
            "detailed_itinerary": scenario.detailed_itinerary,
            "nearby_recommendations": [asdict(r) for r in scenario.nearby_recommendations],
            "safety_info": asdict(scenario.safety_info),
            "personalization_notes": scenario.personalization_notes,
            "backup_options": scenario.backup_options,
            "carbon_savings": scenario.route.carbon_savings,
            "data_source": "synthetic",
            "generated_at": datetime.now().isoformat()
        }