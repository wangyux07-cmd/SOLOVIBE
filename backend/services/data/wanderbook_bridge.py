"""
城市副本册数据桥接器 - 连接预定执行工具和前端页面C
实时同步预订信息、路线指引和打卡状态
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime
import asyncio
from enum import Enum

from data_types import ThreadState
from db.supabase_client import SupabaseClient


logger = logging.getLogger(__name__)


class WanderbookEntryStatus(Enum):
    """城市副本册条目状态"""
    PENDING_CHECKIN = "pending_checkin"     # 待打卡
    IN_PROGRESS = "in_progress"             # 进行中
    COMPLETED = "completed"                 # 已完成
    CANCELLED = "cancelled"                 # 已取消
    EXPIRED = "expired"                     # 已过期


class WanderbookEntryType(Enum):
    """城市副本册条目类型"""
    PLAYWRIGHT_BOOKING = "playwright_booking"   # Playwright自动预约
    MANUAL_BOOKING = "manual_booking"           # 手动预约
    AMAP_POI_DISCOVERY = "amap_poi_discovery"   # 高德发现
    SCENARIO_GENERATED = "scenario_generated"   # 方案生成


@dataclass
class WanderbookEntry:
    """城市副本册条目数据类"""
    id: str
    user_id: str
    booking_id: str
    poi_id: str
    merchant_name: str
    merchant_coordinates: str  # 经纬度 "经度,纬度"
    merchant_address: str
    business_area: str
    
    booking_time: Optional[str] = None
    checkin_time: Optional[str] = None
    
    status: WanderbookEntryStatus = WanderbookEntryStatus.PENDING_CHECKIN
    entry_type: WanderbookEntryType = WanderbookEntryType.PLAYWRIGHT_BOOKING
    
    # 路线信息
    route_info: Dict[str, Any] = None
    walking_distance: str = ""
    estimated_duration: str = ""
    
    # 预约详情
    form_data: Dict[str, Any] = None
    additional_notes: str = ""
    
    # 图片和证据
    screenshot_url: str = ""
    checkin_photo_url: str = ""
    
    # 时间戳
    created_at: str = ""
    updated_at: str = ""
    checkin_deadline: str = ""
    
    # 扩展信息
    weather_info: Dict[str, Any] = None
    personal_notes: str = ""
    mood_rating: int = 0  # 体验评分 1-5分
    
    def __post_init__(self):
        now = datetime.now().isoformat()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now
        
        if self.route_info is None:
            self.route_info = {}
        if self.form_data is None:
            self.form_data = {}
        if self.weather_info is None:
            self.weather_info = {}


class WanderbookBridge:
    """
    城市副本册数据桥接器
    负责将预订信息同步到城市副本册，并支持前端实时更新
    """
    
    def __init__(self, supabase_client: SupabaseClient = None):
        self.supabase_client = supabase_client
        self.sse_connections = {}  # 简单的SSE连接管理（生产环境建议使用Redis）
        
    async def create_entry_from_booking(self, 
                                      booking_result: Any,
                                      poi_info: Any,
                                      user_id: str = "current_user") -> str:
        """
        从预订结果创建城市副本册条目
        
        Args:
            booking_result: 预订执行结果（PlaywrightBookingResult或其他）
            poi_info: POI信息（AmapPoiResult或其他）
            user_id: 用户ID
            
        Returns:
            entry_id: 创建的条目ID
        """
        try:
            entry_id = f"wanderbook_{booking_result.booking_id}"
            
            # 解析商家坐标
            coordinates = "116.397470,39.908823"  # 默认坐标
            if hasattr(poi_info, 'location') and poi_info.location:
                coordinates = poi_info.location
            elif isinstance(poi_info, dict) and 'location' in poi_info:
                coordinates = poi_info['location']
                
            # 解析营业时间
            booking_time = None
            if hasattr(booking_result, 'form_data') and booking_result.form_data:
                booking_time = booking_result.form_data.get('time') or booking_result.form_data.get('booking_time')
            
            # 创建条目
            entry = WanderbookEntry(
                id=entry_id,
                user_id=user_id,
                booking_id=booking_result.booking_id,
                poi_id=getattr(poi_info, 'id', '') or poi_info.get('id', ''),
                merchant_name=getattr(poi_info, 'name', '') or poi_info.get('name', ''),
                merchant_coordinates=coordinates,
                merchant_address=getattr(poi_info, 'address', '') or poi_info.get('address', ''),
                business_area=getattr(poi_info, 'business_area', '') or poi_info.get('business_area', ''),
                booking_time=booking_time,
                form_data=getattr(booking_result, 'form_data', {}),
                screenshot_url=getattr(booking_result, 'screenshot_url', ''),
                entry_type=WanderbookEntryType.PLAYWRIGHT_BOOKING,
                checkin_deadline=self._calculate_checkin_deadline(booking_time)
            )
            
            # 保存到数据库
            await self._save_to_supabase(entry)
            
            # 触发前端推送
            await self._broadcast_entry_update(entry_id, 'created', entry)
            
            logger.info(f"城市副本册条目创建成功: {entry_id}")
            
            return entry_id
            
        except Exception as e:
            logger.error(f"创建城市副本册条目失败: {e}")
            raise
    
    async def create_entry_from_scenario(self,
                                       scenario_info: Dict[str, Any],
                                       user_id: str = "current_user") -> str:
        """
        从场景方案创建城市副本册条目（兼容合成数据）
        """
        try:
            # 生成唯一ID
            scenario_id = scenario_info.get('scenario_id', f"scenario_{datetime.now().strftime('%Y%m%d%H%M%S')}")
            entry_id = f"wanderbook_{scenario_id}"
            
            # 从场景信息中提取商家数据
            merchant_info = scenario_info.get('merchant_info', {})
            
            entry = WanderbookEntry(
                id=entry_id,
                user_id=user_id,
                booking_id=scenario_id,
                poi_id=merchant_info.get('id', ''),
                merchant_name=merchant_info.get('name', ''),
                merchant_coordinates=merchant_info.get('location', {}).get('coordinates', '116.397470,39.908823'),
                merchant_address=merchant_info.get('address', ''),
                business_area=merchant_info.get('location', {}).get('area', ''),
                entry_type=WanderbookEntryType.SCENARIO_GENERATED,
                form_data={
                    'scenario_title': scenario_info.get('title', ''),
                    'scenario_type': scenario_info.get('type', 'healing')
                }
            )
            
            # 保存到数据库
            await self._save_to_supabase(entry)
            
            # 触发前端推送
            await self._broadcast_entry_update(entry_id, 'created', entry)
            
            logger.info(f"城市副本册条目（场景）创建成功: {entry_id}")
            
            return entry_id
            
        except Exception as e:
            logger.error(f"创建城市副本册条目（场景）失败: {e}")
            raise
    
    async def update_entry_status(self, 
                                entry_id: str, 
                                status: WanderbookEntryStatus,
                                user_id: str = "current_user",
                                additional_data: Dict[str, Any] = None) -> bool:
        """
        更新条目状态
        """
        try:
            # 检查条目是否存在
            entry = await self.get_entry(entry_id, user_id)
            if not entry:
                raise ValueError(f"条目不存在: {entry_id}")
                
            # 更新状态
            entry.status = status
            entry.updated_at = datetime.now().isoformat()
            
            # 处理状态相关逻辑
            if status == WanderbookEntryStatus.IN_PROGRESS:
                entry.checkin_time = datetime.now().isoformat()
            elif status == WanderbookEntryStatus.COMPLETED:
                if not entry.checkin_time:
                    entry.checkin_time = datetime.now().isoformat()
                    
            # 更新额外数据
            if additional_data:
                for key, value in additional_data.items():
                    if hasattr(entry, key):
                        setattr(entry, key, value)
                        
            # 保存更新
            await self._save_to_supabase(entry)
            
            # 触发前端推送
            await self._broadcast_entry_update(entry_id, 'updated', entry)
            
            logger.info(f"城市副本册条目状态更新成功: {entry_id} -> {status.value}")
            
            return True
            
        except Exception as e:
            logger.error(f"更新城市副本册条目状态失败: {e}")
            return False
    
    async def get_entry(self, entry_id: str, user_id: str = "current_user") -> Optional[WanderbookEntry]:
        """获取单个条目详情"""
        try:
            entries = await self.get_user_entries(user_id, [entry_id])
            return entries[0] if entries else None
            
        except Exception as e:
            logger.error(f"获取城市副本册条目失败: {e}")
            return None
    
    async def get_user_entries(self, 
                             user_id: str = "current_user",
                             specific_ids: List[str] = None,
                             status_filter: List[WanderbookEntryStatus] = None) -> List[WanderbookEntry]:
        """
        获取用户的全部或指定条目
        """
        try:
            # TODO: 实现实际的数据库查询
            # 这里暂时返回空列表，实际需要连接Supabase查询
            
            if not self.supabase_client:
                logger.warning("Supabase客户端未配置，返回模拟数据")
                return self._get_mock_entries(user_id)
                
            # 实际数据库查询逻辑
            query_params = {
                'user_id': user_id
            }
            
            if specific_ids:
                query_params['id'] = specific_ids
                
            if status_filter:
                query_params['status'] = [status.value for status in status_filter]
            
            # TODO: 实现实际的Supabase查询
            # raw_entries = await self.supabase_client.table('wanderbook_entries').select('*').match(query_params)
            
            return []  # 暂时返回空列表
            
        except Exception as e:
            logger.error(f"获取用户城市副本册条目失败: {e}")
            return []
    
    async def add_checkin_evidence(self,
                                 entry_id: str,
                                 photo_url: str,
                                 user_notes: str = "",
                                 mood_rating: int = 0,
                                 user_id: str = "current_user") -> bool:
        """
        添加打卡证据（照片、笔记、评分）
        """
        try:
            entry = await self.get_entry(entry_id, user_id)
            if not entry:
                return False
                
            # 更新证据信息
            entry.checkin_photo_url = photo_url
            entry.personal_notes = user_notes
            entry.mood_rating = max(1, min(5, mood_rating))  # 限制在1-5分
            entry.updated_at = datetime.now().isoformat()
            
            # 如果之前状态不是已完成，则设置为已完成
            if entry.status != WanderbookEntryStatus.COMPLETED:
                entry.status = WanderbookEntryStatus.COMPLETED
                if not entry.checkin_time:
                    entry.checkin_time = datetime.now().isoformat()
            
            # 保存更新
            await self._save_to_supabase(entry)
            
            # 触发前端推送
            await self._broadcast_entry_update(entry_id, 'evidence_added', entry)
            
            logger.info(f"打卡证据添加成功: {entry_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"添加打卡证据失败: {e}")
            return False
    
    async def sync_with_booking_tool(self, 
                                   booking_tool_result: Any,
                                   poi_data: Any,
                                   user_id: str = "current_user") -> str:
        """
        与预订执行工具同步，建立完整的闭环
        """
        try:
            # 检查是否已存在对应条目
            existing_entry = await self.find_entry_by_booking_id(booking_tool_result.booking_id)
            
            if existing_entry:
                # 更新现有条目
                return await self._update_entry_from_booking(
                    existing_entry, booking_tool_result, poi_data
                )
            else:
                # 创建新条目
                return await self.create_entry_from_booking(
                    booking_tool_result, poi_data, user_id
                )
                
        except Exception as e:
            logger.error(f"与预订工具同步失败: {e}")
            raise
    
    async def find_entry_by_booking_id(self, booking_id: str) -> Optional[WanderbookEntry]:
        """根据booking_id查找条目"""
        # TODO: 实现实际的数据库查询
        # 暂时返回None
        return None
    
    async def _update_entry_from_booking(self,
                                       entry: WanderbookEntry,
                                       booking_result: Any,
                                       poi_data: Any) -> str:
        """从预订结果更新现有条目"""
        try:
            # 更新表单数据
            if hasattr(booking_result, 'form_data'):
                entry.form_data.update(booking_result.form_data)
                
            # 更新截图URL
            if hasattr(booking_result, 'screenshot_url') and booking_result.screenshot_url:
                entry.screenshot_url = booking_result.screenshot_url
                
            # 更新状态
            if hasattr(booking_result, 'success') and booking_result.success:
                if hasattr(booking_result, 'requires_confirmation') and booking_result.requires_confirmation:
                    entry.status = WanderbookEntryStatus.PENDING_CHECKIN  # 等待用户确认
                else:
                    entry.status = WanderbookEntryStatus.IN_PROGRESS  # 预约成功，等待打卡
                    
            entry.updated_at = datetime.now().isoformat()
            
            # 保存更新
            await self._save_to_supabase(entry)
            
            # 触发前端推送
            await self._broadcast_entry_update(entry.id, 'updated', entry)
            
            return entry.id
            
        except Exception as e:
            logger.error(f"更新条目失败: {e}")
            return entry.id
    
    async def _save_to_supabase(self, entry: WanderbookEntry):
        """保存条目到Supabase"""
        try:
            if not self.supabase_client:
                logger.debug("Supabase客户端未配置，跳过保存")
                return
                
            # 转换为字典格式
            entry_data = asdict(entry)
            
            # 转换枚举值为字符串
            if 'status' in entry_data and isinstance(entry_data['status'], Enum):
                entry_data['status'] = entry_data['status'].value
            if 'entry_type' in entry_data and isinstance(entry_data['entry_type'], Enum):
                entry_data['entry_type'] = entry_data['entry_type'].value
                
            # TODO: 实现实际的Supabase插入/更新
            # await self.supabase_client.table('wanderbook_entries').upsert(entry_data)
            
            logger.debug(f"条目已保存到数据库: {entry.id}")
            
        except Exception as e:
            logger.error(f"保存到Supabase失败: {e}")
            # 降级处理：保存到本地缓存
            await self._save_to_local_cache(entry)
    
    async def _save_to_local_cache(self, entry: WanderbookEntry):
        """保存到本地缓存（降级方案）"""
        try:
            import json
            cache_dir = Path("wanderbook_cache")
            cache_dir.mkdir(exist_ok=True)
            
            file_path = cache_dir / f"{entry.id}.json"
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(asdict(entry), f, ensure_ascii=False, indent=2)
                
            logger.info(f"条目已保存到本地缓存: {file_path}")
            
        except Exception as e:
            logger.error(f"本地缓存失败: {e}")
    
    async def _broadcast_entry_update(self, entry_id: str, action: str, entry: WanderbookEntry):
        """广播条目更新（触发前端SSE）"""
        try:
            # 构建更新消息
            message = {
                'event': 'wanderbook_entry_updated',
                'data': {
                    'action': action,
                    'entry_id': entry_id,
                    'timestamp': datetime.now().isoformat(),
                    'status': entry.status.value,
                    'merchant_name': entry.merchant_name,
                    'business_area': entry.business_area
                }
            }
            
            # TODO: 实现实际的SSE广播
            # 这里暂时只记录日志
            logger.info(f"待广播的消息: {message}")
            
        except Exception as e:
            logger.error(f"广播条目更新失败: {e}")
    
    def _calculate_checkin_deadline(self, booking_time: Optional[str]) -> str:
        """计算打卡截止时间"""
        try:
            if booking_time:
                # 尝试解析预约时间
                booking_dt = datetime.fromisoformat(booking_time.replace('Z', '+00:00'))
                deadline = booking_dt + timedelta(hours=2)  # 预约后2小时内打卡
            else:
                deadline = datetime.now() + timedelta(days=1)  # 默认24小时内打卡
                
            return deadline.isoformat()
            
        except Exception:
            # 解析失败，返回默认截止时间
            return (datetime.now() + timedelta(days=1)).isoformat()
    
    def _get_mock_entries(self, user_id: str) -> List[WanderbookEntry]:
        """获取模拟数据（开发用）"""
        now = datetime.now()
        return [
            WanderbookEntry(
                id="wanderbook_demo_1",
                user_id=user_id,
                booking_id="demo_booking_1",
                poi_id="amap_poi_123",
                merchant_name="星巴克咖啡(三里屯店)",
                merchant_coordinates="116.455158,39.936407",
                merchant_address="北京市朝阳区三里屯路19号",
                business_area="三里屯",
                booking_time=(now - timedelta(hours=2)).isoformat(),
                status=WanderbookEntryStatus.PENDING_CHECKIN,
                entry_type=WanderbookEntryType.PLAYWRIGHT_BOOKING,
                form_data={'people_num': 2, 'drinks': ['美式咖啡', '拿铁']}
            ),
            WanderbookEntry(
                id="wanderbook_demo_2",
                user_id=user_id,
                booking_id="demo_booking_2",
                poi_id="amap_poi_456",
                merchant_name="朝阳公园",
                merchant_coordinates="116.483223,39.937512",
                merchant_address="北京市朝阳区朝阳公园南路1号",
                business_area="CBD",
                booking_time=(now - timedelta(days=1)).isoformat(),
                checkin_time=(now - timedelta(hours=12)).isoformat(),
                status=WanderbookEntryStatus.COMPLETED,
                entry_type=WanderbookEntryType.SCENARIO_GENERATED,
                mood_rating=5,
                personal_notes="今天的公园漫步非常治愈，看到了美丽的樱花"
            )
        ]