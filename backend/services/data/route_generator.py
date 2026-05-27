"""
路线规划生成器 - 为用户的独自出行提供详细的路线规划和时间安排
"""

from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import random
import math
from .merchant_database import Merchant, Location, MerchantType, get_random_merchant, search_merchants_by_features


@dataclass
class TransportOption:
    """交通方式选项"""
    mode: str  # walking, subway, bus, taxi, bike
    description: str
    duration: int  # 分钟
    cost: float  # 人民币
    carbon_footprint: float  # 碳排放量


@dataclass
class RouteSegment:
    """路线段数据"""
    start_location: str
    end_location: str
    transport: TransportOption
    distance: float  # 公里
    estimated_duration: int  # 分钟


@dataclass
class TimeSlot:
    """时间槽数据"""
    start_time: str  # HH:MM格式
    end_time: str
    activity: str
    location: str
    notes: Optional[str] = None


@dataclass
class DetailedRoute:
    """详细路线规划"""
    total_distance: float  # 总距离(公里)
    total_duration: int  # 总时长(分钟)
    total_cost: float  # 总花费
    carbon_savings: str  # 碳减排描述
    route_segments: List[RouteSegment]
    time_schedule: List[TimeSlot]
    weather_adaptation: str  # 天气适应建议
    emergency_contacts: List[str]  
    nearby_amenities: List[str]  # 附近便民设施


class RouteGenerator:
    """
    路线生成器 - 根据商家信息和用户需求生成完整路线规划
    """
    
    def __init__(self):
        self.transport_options = {
            "walking": {"speed_kmh": 5, "cost_per_km": 0},
            "subway": {"speed_kmh": 35, "cost_per_km": 0.5},
            "bus": {"speed_kmh": 20, "cost_per_km": 0.3},
            "taxi": {"speed_kmh": 30, "cost_per_km": 2.5},
            "bike": {"speed_kmh": 15, "cost_per_km": 0.3}
        }
        
        self.weather_recommendations = {
            "sunny": "天气晴好，适合步行或骑行，记得防晒",
            "cloudy": "阴天舒适，是户外活动的好天气",
            "rainy": "建议乘坐地铁或出租车，带好雨具",
            "hot": "天气较热，建议选择有空调的室内路线",
            "cold": "天气较冷，注意保暖，可选室内路线"
        }
    
    def calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """计算两点间直线距离(km)"""
        # 使用Haversine公式计算球面距离
        R = 6371  # 地球半径(km)
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        return R * c
    
    def generate_transport_options(self, distance: float) -> List[TransportOption]:
        """生成交通方式选项"""
        options = []
        
        # 步行选项
        if distance <= 2:
            duration = int(distance * 60 / self.transport_options["walking"]["speed_kmh"])
            options.append(TransportOption(
                mode="walking",
                description="步行前往，享受沿途风景",
                duration=duration,
                cost=0,
                carbon_footprint=0
            ))
        
        # 地铁选项
        if distance <= 20:
            duration = int(distance * 60 / self.transport_options["subway"]["speed_kmh"] + 15)
            cost = max(3, distance * self.transport_options["subway"]["cost_per_km"])
            options.append(TransportOption(
                mode="subway",
                description="乘坐地铁，快速便捷",
                duration=duration,
                cost=cost,
                carbon_footprint=distance * 0.05
            ))
        
        # 公交选项
        if distance <= 15:
            duration = int(distance * 60 / self.transport_options["bus"]["speed_kmh"] + 10)
            cost = max(2, distance * self.transport_options["bus"]["cost_per_km"])
            options.append(TransportOption(
                mode="bus",
                description="乘坐公交，经济环保",
                duration=duration,
                cost=cost,
                carbon_footprint=distance * 0.08
            ))
        
        # 出租车选项
        duration = int(distance * 60 / self.transport_options["taxi"]["speed_kmh"] + 5)
        cost = max(15, distance * self.transport_options["taxi"]["cost_per_km"])
        options.append(TransportOption(
            mode="taxi",
            description="打车前往，舒适便捷",
            duration=duration,
            cost=cost,
            carbon_footprint=distance * 0.2
        ))
        
        return options
    
    def generate_time_schedule(self, merchant: Merchant, total_duration: int) -> List[TimeSlot]:
        """生成时间安排表"""
        current_time = datetime.now()
        schedule = []
        
        # 根据商家类型确定活动流程
        if merchant.type in [MerchantType.COFFEE_SHOP, MerchantType.RESTAURANT]:
            # 餐饮场所时间流程
            arrive_time = current_time + timedelta(minutes=10)
            
            schedule.append(TimeSlot(
                start_time=current_time.strftime("%H:%M"),
                end_time=arrive_time.strftime("%H:%M"),
                activity="出发前往",
                location="家/当前位置",
                notes=f"建议乘坐{self._get_recommended_transport(merchant)}前往"
            ))
            
            schedule.append(TimeSlot(
                start_time=arrive_time.strftime("%H:%M"),
                end_time=(arrive_time + timedelta(minutes=total_duration-5)).strftime("%H:%M"),
                activity=f"在{merchant.name}享受时光",
                location=merchant.location.address,
                notes=f"推荐体验: {self._get_merchant_activity(merchant)}"
            ))
            
            schedule.append(TimeSlot(
                start_time=(arrive_time + timedelta(minutes=total_duration-5)).strftime("%H:%M"),
                end_time=(arrive_time + timedelta(minutes=total_duration)).strftime("%H:%M"),
                activity="准备离开",
                location=merchant.location.address,
                notes="整理随身物品，检查时间"
            ))
            
        elif merchant.type == MerchantType.PARK:
            # 公园时间流程
            arrive_time = current_time + timedelta(minutes=15)
            
            schedule.append(TimeSlot(
                start_time=current_time.strftime("%H:%M"),
                end_time=arrive_time.strftime("%H:%M"),
                activity="前往公园",
                location="家/当前位置",
                notes="带上水和小零食"
            ))
            
            schedule.append(TimeSlot(
                start_time=arrive_time.strftime("%H:%M"),
                end_time=(arrive_time + timedelta(minutes=total_duration)).strftime("%H:%M"),
                activity="在公园漫步",
                location=merchant.location.address,
                notes="可以选择湖边散步或林间小径"
            ))
        
        return schedule
    
    def _get_recommended_transport(self, merchant: Merchant) -> str:
        """获取推荐交通方式"""
        # 距离假设为用户当前位置到商家的平均距离
        average_distance = random.uniform(2, 8)
        options = self.generate_transport_options(average_distance)
        
        # 偏好绿色出行
        pref_order = ["walking", "bike", "subway", "bus", "taxi"]
        for pref in pref_order:
            for option in options:
                if option.mode == pref:
                    return option.description
        
        return options[0].description if options else "打车前往"
    
    def _get_merchant_activity(self, merchant: Merchant) -> str:
        """获取商家推荐活动"""
        activities = {
            MerchantType.COFFEE_SHOP: "品尝手冲咖啡，阅读或思考",
            MerchantType.RESTAURANT: "享用慢食，品味美食",
            MerchantType.PARK: "散步、拍照、观察自然",
            MerchantType.BOOKSTORE: "浏览书籍，安静阅读"
        }
        return activities.get(merchant.type, "享受安静时光")
    
    def generate_complete_route(self, 
                              user_location: Tuple[float, float], 
                              merchant: Merchant,
                              duration_minutes: int = 120,
                              preferred_transport: str = "auto") -> DetailedRoute:
        """生成完整路线规划"""
        
        # 计算距离
        distance = self.calculate_distance(
            user_location[0], user_location[1], 
            merchant.location.latitude, merchant.location.longitude
        )
        
        # 生成交通选项
        transport_options = self.generate_transport_options(distance)
        
        # 选择推荐交通方式
        if preferred_transport == "auto" or preferred_transport not in [t.mode for t in transport_options]:
            recommended_transport = min(transport_options, key=lambda t: (t.cost, t.duration))
        else:
            recommended_transport = next(t for t in transport_options if t.mode == preferred_transport)
        
        # 生成时间安排
        time_schedule = self.generate_time_schedule(merchant, duration_minutes)
        
        # 生成路线段
        route_segments = [
            RouteSegment(
                start_location="当前地点",
                end_location=f"{merchant.name} - {merchant.location.address}",
                transport=recommended_transport,
                distance=distance,
                estimated_duration=duration_minutes
            )
        ]
        
        # 估算总费用
        if merchant.type in [MerchantType.COFFEE_SHOP, MerchantType.RESTAURANT]:
            estimated_cost = random.uniform(40, 80)  # 餐费
        elif merchant.type == MerchantType.BOOKSTORE:
            estimated_cost = random.uniform(0, 30)   # 可能的购书费
        else:
            estimated_cost = 0  # 公园免费
        
        total_cost = recommended_transport.cost + estimated_cost
        
        # 碳减排描述
        carbon_savings = "选择绿色出行，比驾车减少约{:.1f}kg碳排放".format(
            distance * (0.2 - recommended_transport.carbon_footprint)
        ) if recommended_transport.mode in ["walking", "bike", "subway", "bus"] else ""
        
        # 天气适应性
        weather_adaptation = self.weather_recommendations["sunny"]  # 默认为晴天建议
        
        # 应急联系和便民设施
        emergency_contacts = [f"{merchant.name}: {merchant.contact}", "紧急救援: 110"]
        nearby_amenities = [
            "便利店: 全家便利店",
            "ATM: 工商银行ATM",
            "地铁站: {}站".format(merchant.location.area),
            "医院: 附近社区卫生中心"
        ]
        
        return DetailedRoute(
            total_distance=round(distance, 2),
            total_duration=duration_minutes,
            total_cost=round(total_cost, 2),
            carbon_savings=carbon_savings,
            route_segments=route_segments,
            time_schedule=time_schedule,
            weather_adaptation=weather_adaptation,
            emergency_contacts=emergency_contacts,
            nearby_amenities=nearby_amenities
        )


# === 特定场景的完整方案生成器 ===

class CompleteScenarioGenerator:
    """
    完整场景生成器 - 为特定用户心境生成包含所有细节的完整方案
    """
    
    def __init__(self):
        self.route_generator = RouteGenerator()
    
    def generate_healing_scenario(self, user_message: str) -> Dict[str, Any]:
        """生成治愈系方案"""
        # 选择治愈系商家
        healing_merchants = search_merchants_by_features(["安静", "治愈", "放松"])
        if not healing_merchants:
            healing_merchants = search_merchants_by_features(["安静", "书", "自然"])
        
        merchant = random.choice(healing_merchants) if healing_merchants else get_random_merchant(MerchantType.COFFEE_SHOP)
        
        # 用户模拟位置(北京市中心区域)
        user_location = (39.9042, 116.4074)  # 天安门附近
        
        # 生成路线
        route = self.route_generator.generate_complete_route(
            user_location, merchant, duration_minutes=90, preferred_transport="walking"
        )
        
        # 生成套餐推荐
        recommended_package = None
        if merchant.packages:
            recommended_package = random.choice(merchant.packages)
        
        return {
            "type": "healing_journey",
            "merchant": merchant,
            "route": route,
            "recommended_activities": [
                "深呼吸练习，观察内心",
                f"品尝{recommended_package.name if recommended_package else '特色产品'}",
                "写下此刻的感受",
                "观察周围的环境细节"
            ],
            "mindful_tips": [
                "专注于当下的每一个感受",
                "不用担心时间，慢慢来",
                "如果感到累，可以稍作休息",
                "享受一个人的宁静时光"
            ],
            "cost_breakdown": {
                "transportation": route.total_cost - (recommended_package.discounted_price if recommended_package else 0),
                "consumption": recommended_package.discounted_price if recommended_package else random.uniform(25, 45),
                "total": route.total_cost
            }
        }
    
    def generate_exploration_scenario(self, user_message: str) -> Dict[str, Any]:
        """生成探索系方案"""
        # 根据用户兴趣选择商家类型
        interest_keywords = {
            "艺术": MerchantType.ART_GALLERY,
            "文化": MerchantType.MUSEUM, 
            "自然": MerchantType.PARK,
            "阅读": MerchantType.BOOKSTORE,
            "咖啡": MerchantType.COFFEE_SHOP
        }
        
        selected_type = MerchantType.COFFEE_SHOP  # 默认
        for keyword, mtype in interest_keywords.items():
            if keyword in user_message:
                selected_type = mtype
                break
        
        merchant = get_random_merchant(selected_type)
        
        user_location = (39.9042, 116.4074)
        route = self.route_generator.generate_complete_route(
            user_location, merchant, duration_minutes=150
        )
        
        return {
            "type": "exploration_journey",
            "merchant": merchant,
            "route": route,
            "recommended_activities": [
                "探索周边环境",
                "与店员简短交流获取建议",
                "记录有趣的发现",
                "尝试新体验"
            ],
            "exploration_prompts": [
                "这里有什么特别的设计细节？",
                "店员有什么推荐的理由？",
                "这里的环境如何影响你的心情？",
                "你会如何向朋友推荐这里？"
            ]
        }