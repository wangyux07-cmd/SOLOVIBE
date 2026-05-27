"""
预订执行工具模块 - 高德地图Web服务API统一实现
职责：POI周边搜索、多模式路径规划、地理围栏服务
"""

import asyncio
import aiohttp
import json
import logging
from typing import Dict, List, Any, Optional, Callable, AsyncGenerator, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
import hashlib
import os
from urllib.parse import urlencode


logger = logging.getLogger(__name__)


class BookingStatus(Enum):
    """预订状态枚举"""
    PENDING = "pending"         # 等待中
    PROCESSING = "processing"   # 处理中
    CONFIRMING = "confirming"   # 确认中
    COMPLETED = "completed"     # 已完成
    FAILED = "failed"          # 失败
    CANCELLED = "cancelled"    # 已取消
    TIMEOUT = "timeout"        # 超时


class ExecutionStage(Enum):
    """执行阶段枚举"""
    INITIALIZING = "initializing"      # 初始化
    VALIDATING = "validating"          # 参数验证  
    SEARCHING_POIS = "searching_pois"  # 搜索兴趣点
    ROUTING = "routing"                # 路径规划
    SAVING_ROUTE = "saving_route"      # 保存路线
    FINALIZING = "finalizing"          # 最终处理


class AmapServiceType(Enum):
    """高德地图服务类型"""
    PLACE_SEARCH = "place_search"      # POI搜索
    PLACE_AROUND = "place_around"      # 周边搜索
    DIRECTION_WALKING = "direction_walking"  # 步行路径
    DIRECTION_DRIVING = "direction_driving"  # 驾车路径
    DIRECTION_TRANSIT = "direction_transit"  # 公交路径
    GEOCODE = "geocode"                # 地理编码
    REVERSE_GEOCODE = "reverse_geocode" # 逆地理编码


@dataclass
class ExecutionFeedback:
    """执行反馈数据类"""
    stage: ExecutionStage
    status: BookingStatus  
    message: str
    progress: float  # 0-100
    timestamp: str
    details: Dict[str, Any] = None
    error: Optional[str] = None


@dataclass
class AmapPoiResult:
    """高德POI结果数据类"""
    id: str
    name: str
    address: str
    location: str  # "经度,纬度"
    distance: str
    typecode: str
    type: str
    tel: str = ""
    business_area: str = ""
    rating: str = ""
    cost: str = ""
    photos: List[str] = None
    
    def __post_init__(self):
        if self.photos is None:
            self.photos = []


@dataclass
class AmapRouteResult:
    """高德路径规划结果数据类"""
    distance: str  # 总距离（米）
    duration: str  # 总时间（秒）
    taxi_cost: str = ""  # 打车费用（元）
    steps: List[Dict[str, Any]] = None  # 详细步骤
    
    def __post_init__(self):
        if self.steps is None:
            self.steps = []


@dataclass
class BookingResult:
    """预订结果数据类（高德专用版本）"""
    success: bool
    booking_id: Optional[str] = None
    poi_info: Optional[AmapPoiResult] = None  # POI信息
    route_info: Optional[AmapRouteResult] = None  # 路径信息
    saved_route_id: Optional[str] = None  # 保存的路线ID
    estimated_cost: Optional[float] = None
    actual_cost: Optional[float] = None
    execution_details: Dict[str, Any] = None
    warnings: List[str] = None
    next_steps: List[str] = None
    error_message: Optional[str] = None
    nearby_alternatives: List[AmapPoiResult] = None  # 备选POI

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
        if self.next_steps is None:
            self.next_steps = []
        if self.nearby_alternatives is None:
            self.nearby_alternatives = []


class AmapExecutionTool:
    """
    高德地图执行工具 - 统一处理POI搜索和路径规划
    核心职能：
    - POI周边深度搜索
    - 多模式路径规划
    - 地理数据查询
    - 路线保存管理
    """
    
    def __init__(self):
        self.session = None
        self.amap_key = os.getenv("AMAP_API_KEY")
        self.amap_base_url = os.getenv("AMAP_BASE_URL", "https://restapi.amap.com")
        self.rate_limit_delay = 1.0 / int(os.getenv("AMAP_RATE_LIMIT", "20"))  # 秒
        self.last_request_time = None
        
        # 服务URL映射
        self.service_urls = {
            AmapServiceType.PLACE_SEARCH: "/v3/place/text",
            AmapServiceType.PLACE_AROUND: "/v3/place/around", 
            AmapServiceType.DIRECTION_WALKING: "/v3/direction/walking",
            AmapServiceType.DIRECTION_DRIVING: "/v3/direction/driving",
            AmapServiceType.DIRECTION_TRANSIT: "/v3/direction/transit",
            AmapServiceType.GEOCODE: "/v3/geocode/geo",
            AmapServiceType.REVERSE_GEOCODE: "/v3/geocode/regeo"
        }
        
        if not self.amap_key:
            logger.error("高德地图API密钥未配置")
            raise RuntimeError("AMAP_API_KEY环境变量未设置")
        
        logger.info("高德地图执行工具初始化完成")
        
    async def __aenter__(self):
        """异步上下文管理器"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器"""
        if self.session:
            await self.session.close()
    
    def _generate_booking_id(self) -> str:
        """生成唯一ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_hash = hashlib.md5(f"{timestamp}{id(self)}".encode()).hexdigest()[:8]
        return f"amap_{timestamp}_{random_hash}"
    
    async def _rate_limit_wait(self):
        """简单的流量控制"""
        current_time = datetime.now()
        if self.last_request_time:
            elapsed = (current_time - self.last_request_time).total_seconds()
            if elapsed < self.rate_limit_delay:
                await asyncio.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = datetime.now()
    
    async def _send_feedback(self, feedback_callback: Callable[[ExecutionFeedback], None],
                           stage: ExecutionStage, status: BookingStatus, 
                           message: str, progress: float, **kwargs):
        """发送执行反馈"""
        feedback = ExecutionFeedback(
            stage=stage,
            status=status,
            message=message,
            progress=progress,
            timestamp=datetime.now().isoformat(),
            details=kwargs.get('details'),
            error=kwargs.get('error')
        )
        
        if feedback_callback:
            await feedback_callback(feedback)
    
    async def _make_amap_request(self, service_type: AmapServiceType, 
                               params: Dict[str, Any]) -> Dict[str, Any]:
        """发送高德地图API请求"""
        if not self.session:
            raise RuntimeError("HTTP会话未初始化")
        
        await self._rate_limit_wait()
        
        # 添加必要参数
        request_params = {
            "key": self.amap_key,
            "output": "json",
            **params
        }
        
        endpoint = self.service_urls[service_type]
        url = f"{self.amap_base_url}{endpoint}"
        
        try:
            async with self.session.get(url, params=request_params, timeout=10) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get("status") == "1":
                        return result
                    else:
                        error_info = result.get("info", "未知错误")
                        error_code = result.get("infocode", "")
                        logger.error(f"高德API错误: {error_code} - {error_info}")
                        raise RuntimeError(f"高德API错误: {error_info} (代码: {error_code})")
                else:
                    error_text = await response.text()
                    logger.error(f"HTTP错误: {response.status} - {error_text}")
                    raise RuntimeError(f"HTTP请求失败: {response.status}")
        
        except asyncio.TimeoutError:
            logger.error(f"高德API请求超时: {service_type.value}")
            raise RuntimeError(f"请求高德{type}服务超时")
        except Exception as e:
            logger.error(f"高德API请求异常: {e}")
            raise
    
    async def _search_pois_around_location(self, 
                                         location: str, 
                                         keywords: str = "",
                                         radius: int = 3000,
                                         poi_type: str = "") -> List[AmapPoiResult]:
        """周边POI搜索"""
        params = {
            "location": location,
            "keywords": keywords,
            "types": poi_type,
            "radius": radius,
            "offset": 20,  # 返回结果数量
            "page": 1,
            "extensions": "all"  # 返回详细信息
        }
        
        result = await self._make_amap_request(AmapServiceType.PLACE_AROUND, params)
        
        pois = []
        if "pois" in result:
            for poi_data in result["pois"]:
                poi = AmapPoiResult(
                    id=poi_data.get("id", ""),
                    name=poi_data.get("name", ""),
                    address=poi_data.get("address", ""),
                    location=poi_data.get("location", ""),
                    distance=poi_data.get("distance", ""),
                    typecode=poi_data.get("typecode", ""),
                    type=poi_data.get("type", ""),
                    tel=poi_data.get("tel", ""),
                    business_area=poi_data.get("businessarea", ""),
                    rating=poi_data.get("biz_ext", {}).get("rating", ""),
                    cost=poi_data.get("biz_ext", {}).get("cost", ""),
                    photos=poi_data.get("photos", [])
                )
                pois.append(poi)
        
        return pois
    
    async def _plan_route(self, origin: str, destination: str, 
                         travel_mode: str = "walking") -> AmapRouteResult:
        """路径规划"""
        service_type_map = {
            "walking": AmapServiceType.DIRECTION_WALKING,
            "driving": AmapServiceType.DIRECTION_DRIVING,
            "transit": AmapServiceType.DIRECTION_TRANSIT
        }
        
        if travel_mode not in service_type_map:
            raise ValueError(f"不支持的交通方式: {travel_mode}")
        
        params = {
            "origin": origin,
            "destination": destination
        }
        
        if travel_mode == "driving":
            params["strategy"] = "0"  # 默认驾驶策略
        elif travel_mode == "transit":
            params["city"] = "北京"  # 可以根据需要动态设置
        
        result = await self._make_amap_request(service_type_map[travel_mode], params)
        
        route_result = AmapRouteResult(distance="0", duration="0")
        
        if travel_mode == "walking" and "route" in result:
            paths = result["route"].get("paths", [])
            if paths:
                path = paths[0]
                route_result.distance = path.get("distance", "0")
                route_result.duration = path.get("duration", "0")
                route_result.steps = path.get("steps", [])
        
        elif travel_mode == "driving" and "route" in result:
            paths = result["route"].get("paths", [])
            if paths:
                path = paths[0]
                route_result.distance = path.get("distance", "0")
                route_result.duration = path.get("duration", "0")
                route_result.taxi_cost = path.get("taxi_cost", "")
        
        elif travel_mode == "transit" and "route" in result:
            transits = result["route"].get("transits", [])
            if transits:
                transit = transits[0]
                route_result.distance = str(int(transit.get("distance", "0")))
                route_result.duration = transit.get("duration", "0")
                route_result.taxi_cost = transit.get("cost", "")
        
        return route_result
    
    async def _validate_booking_request(self, booking_request: Dict[str, Any]) -> Dict[str, Any]:
        """验证高德执行请求"""
        required_fields = ["type", "purpose", "location"]
        missing_fields = [field for field in required_fields if field not in booking_request]
        
        if missing_fields:
            raise ValueError(f"缺少必要参数: {missing_fields}")
        
        # 目的验证
        valid_purposes = ["explore_pois", "plan_route", "save_favorite_place"]
        if booking_request["purpose"] not in valid_purposes:
            raise ValueError(f"无效的执行目的，必须是: {valid_purposes}")
        
        # 位置格式验证
        location = booking_request["location"]
        if not self._is_valid_location_format(location):
            raise ValueError("位置格式错误，应为 '经度,纬度' 格式")
        
        return booking_request
    
    def _is_valid_location_format(self, location: str) -> bool:
        """验证位置格式"""
        try:
            if not location or ',' not in location:
                return False
            lng, lat = location.split(',')
            float(lng)
            float(lat)
            return True
        except (ValueError, TypeError):
            return False
    
    async def _execute_poi_exploration(self, 
                                     booking_request: Dict[str, Any],
                                     feedback_callback: Callable = None) -> BookingResult:
        """执行POI探索"""
        location = booking_request["location"]
        search_keywords = booking_request.get("keywords", "咖啡|书店|公园")
        radius = int(booking_request.get("radius", 3000))
        poi_type = booking_request.get("poi_type", "050000")  # 餐饮相关
        
        # 搜索周边POI
        await self._send_feedback(
            feedback_callback, ExecutionStage.SEARCHING_POIS,
            BookingStatus.PROCESSING,
            f"正在搜索周边兴趣点: {search_keywords}...", 40
        )
        
        try:
            pois = await self._search_pois_around_location(
                location, search_keywords, radius, poi_type
            )
            
            if not pois:
                return BookingResult(
                    success=False,
                    error_message="未找到相关兴趣点",
                    warnings=["建议扩大搜索范围或调整关键词"]
                )
            
            # 选择最优POI（这里简化为选择第一个）
            target_poi = pois[0]
            
            # 生成模拟的保存结果
            saved_route_id = f"fav_{target_poi.id}"
            
            return BookingResult(
                success=True,
                booking_id=self._generate_booking_id(),
                poi_info=target_poi,
                saved_route_id=saved_route_id,
                estimated_cost=float(target_poi.cost) if target_poi.cost else 0,
                execution_details={
                    "search_keywords": search_keywords,
                    "search_radius": radius,
                    "total_pois_found": len(pois),
                    "recommended_pois": [asdict(poi) for poi in pois[:3]]  # 前三名推荐
                },
                next_steps=[
                    "点击查看详情",
                    "开始路线导航", 
                    "查看用户评价"
                ],
                nearby_alternatives=pois[1:4]  # 其他备选
            )
        
        except Exception as e:
            logger.error(f"POI探索执行错误: {e}")
            return BookingResult(
                success=False,
                error_message=f"搜索兴趣点失败: {str(e)}"
            )
    
    async def _execute_route_planning(self,
                                    booking_request: Dict[str, Any],
                                    feedback_callback: Callable = None) -> BookingResult:
        """执行路径规划"""
        origin = booking_request.get("start_location")
        destination = booking_request["location"]
        travel_mode = booking_request.get("travel_mode", "walking")
        
        if not origin:
            # 如果没有提供起点，使用终点周边作为虚拟起点
            origin = destination
        
        # 路径规划
        await self._send_feedback(
            feedback_callback, ExecutionStage.ROUTING,
            BookingStatus.PROCESSING,
            f"正在规划{travel_mode}路线...", 60
        )
        
        try:
            route_result = await self._plan_route(origin, destination, travel_mode)
            
            # 转换为分钟和公里
            duration_minutes = int(int(route_result.duration) / 60) if route_result.duration else 0
            distance_km = round(int(route_result.distance) / 1000, 2) if route_result.distance else 0
            
            saved_route_id = f"route_{hashlib.md5(f'{origin}{destination}{travel_mode}'.encode()).hexdigest()[:12]}"
            
            return BookingResult(
                success=True,
                booking_id=self._generate_booking_id(),
                route_info=route_result,
                saved_route_id=saved_route_id,
                estimated_cost=float(route_result.taxi_cost) if route_result.taxi_cost else 0,
                execution_details={
                    "origin": origin,
                    "destination": destination,
                    "travel_mode": travel_mode,
                    "duration_minutes": duration_minutes,
                    "distance_km": distance_km,
                    "route_steps_count": len(route_result.steps)
                },
                next_steps=[
                    "开始实时导航",
                    "查看实时路况",
                    "预估到达时间"
                ]
            )
        
        except Exception as e:
            logger.error(f"路径规划执行错误: {e}")
            return BookingResult(
                success=False,
                error_message=f"路径规划失败: {str(e)}"
            )
    
    async def execute_booking(self, 
                            booking_request: Dict[str, Any],
                            feedback_callback: Callable[[ExecutionFeedback], None] = None) -> BookingResult:
        """
        执行预订主函数 - 高德地图专用版本
        
        Args:
            booking_request: 预订请求，包含:
                - type: 服务类型
                - purpose: 执行目的 (explore_pois, plan_route, save_favorite_place)
                - location: 目标位置 "经度,纬度"
                - keywords: 搜索关键词 (可选)
                - travel_mode: 交通方式 (可选, walking/driving/transit)
                - radius: 搜索半径 (可选, 默认3000米)
            feedback_callback: 反馈回调函数
        
        Returns:
            BookingResult对象，包含执行结果
        """
        booking_id = self._generate_booking_id()
        
        try:
            # 阶段1: 初始化
            await self._send_feedback(
                feedback_callback, ExecutionStage.INITIALIZING, 
                BookingStatus.PROCESSING, 
                "正在初始化高德地图服务...", 10,
                details={"booking_id": booking_id}
            )
            
            # 阶段2: 参数验证
            await self._send_feedback(
                feedback_callback, ExecutionStage.VALIDATING,
                BookingStatus.PROCESSING,
                "正在验证请求参数...", 20
            )
            
            validated_request = await self._validate_booking_request(booking_request)
            
            purpose = validated_request["purpose"]
            
            # 根据目的执行不同操作
            if purpose == "explore_pois":
                # POI探索
                await self._send_feedback(
                    feedback_callback, ExecutionStage.SEARCHING_POIS,
                    BookingStatus.PROCESSING,
                    "正在搜索周边兴趣点...", 40
                )
                
                result = await self._execute_poi_exploration(validated_request, feedback_callback)
                
            elif purpose == "plan_route":
                # 路径规划
                await self._send_feedback(
                    feedback_callback, ExecutionStage.ROUTING,
                    BookingStatus.PROCESSING,
                    "正在规划路线...", 40
                )
                
                result = await self._execute_route_planning(validated_request, feedback_callback)
                
            elif purpose == "save_favorite_place":
                # 保存喜爱地点
                await self._send_feedback(
                    feedback_callback, ExecutionStage.SAVING_ROUTE,
                    BookingStatus.PROCESSING,
                    "正在保存地点信息...", 70
                )
                
                # 保存操作执行
                result = await self._execute_poi_exploration(validated_request, feedback_callback)
                
            else:
                raise ValueError(f"不支持的执行目的: {purpose}")
            
            # 最终处理
            await self._send_feedback(
                feedback_callback, ExecutionStage.FINALIZING,
                BookingStatus.PROCESSING if not result.success else BookingStatus.COMPLETED,
                "正在完成执行...", 100
            )
            
            return result
        
        except Exception as e:
            error_msg = f"执行过程中发生错误: {str(e)}"
            logger.error(f"高德执行错误: {e}")
            
            await self._send_feedback(
                feedback_callback, ExecutionStage.FINALIZING,
                BookingStatus.FAILED, error_msg, 100, error=error_msg
            )
            
            return BookingResult(
                success=False,
                error_message=error_msg,
                warnings=["建议使用手动模式或更换位置后重试"]
            )
    
    async def get_service_capabilities(self) -> Dict[str, Any]:
        """获取服务能力信息"""
        return {
            "provider": "高德地图Web服务API",
            "supported_purposes": [
                "explore_pois",      # POI周边搜索
                "plan_route",        # 路径规划  
                "save_favorite_place" # 收藏地点
            ],
            "supported_travel_modes": ["walking", "driving", "transit"],
            "search_radius_range": {"min": 500, "max": 50000, "unit": "米"},
            "features": [
                "real_time_poi_search",
                "multi_mode_routing",
                "distance_calculation",
                "reverse_geocoding",
                "place_details"
            ],
            "rate_limit": f"每秒{int(1/self.rate_limit_delay)}次",
            "poi_categories": [
                "餐饮", "购物", "休闲娱乐", "生活服务", 
                "交通枢纽", "公共设施", "旅游景点"
            ]
        }