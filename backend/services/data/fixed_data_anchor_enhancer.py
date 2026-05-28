"""
数据锚点对齐增强器 - 修复版
通过标准化的数据接口消除模块间契约冲突
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, List, Tuple, Protocol
import logging
from datetime import datetime
import re
from difflib import SequenceMatcher


# ================================
# 🎯 第一阶段：统一数据合同定义
# ================================

class UnifiedPoiInterface(Protocol):
    """统一POI数据接口 - 跨模块数据合同"""
    id: str
    name: str  
    address: str
    location: str
    business_area: str
    type: str
    typecode: str
    rating: Optional[str] = None
    tel: Optional[str] = None


class DataAdapter:
    """数据适配器 - 统一不同来源的数据格式"""
    
    @staticmethod
    def to_unified(poi_data: Any) -> 'UnifiedPoiAdapter':
        """将任意POI数据转换为统一格式"""
        # 提取核心字段映射
        core_fields = {
            'id': poi_data.id if hasattr(poi_data, 'id') else poi_data.get('id', ''),
            'name': poi_data.name if hasattr(poi_data, 'name') else poi_data.get('name', ''),
            'address': poi_data.address if hasattr(poi_data, 'address') else poi_data.get('address', ''),
            'location': poi_data.location if hasattr(poi_data, 'location') else poi_data.get('location', ''),
            'business_area': (poi_data.business_area if hasattr(poi_data, 'business_area') 
                            else poi_data.get('business_area', '')),
            'type': poi_data.type if hasattr(poi_data, 'type') else poi_data.get('type', ''),
            'typecode': poi_data.typecode if hasattr(poi_data, 'typecode') else poi_data.get('typecode', ''),
            'rating': poi_data.rating if hasattr(poi_data, 'rating') else poi_data.get('rating', ''),
            'tel': poi_data.tel if hasattr(poi_data, 'tel') else poi_data.get('tel', '')
        }
        
        return UnifiedPoiAdapter(**core_fields)
    
    @staticmethod  
    def validate_unified(data: 'UnifiedPoiAdapter') -> bool:
        """验证数据完整性"""
        required_fields = ['id', 'name', 'address', 'location', 'business_area']
        return all(getattr(data, f, None) for f in required_fields)


class UnifiedPoiAdapter:
    """统一POI数据结构 - 适配不同来源"""
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        
        # 确保必需字段有默认值
        self.id = self.id or ''
        self.name = self.name or ''
        self.address = self.address or ''
        self.location = self.location or ''
        self.business_area = self.business_area or ''
        self.type = self.type or ''
        self.typecode = self.typecode or ''


logger = logging.getLogger(__name__)


# ================================
# 🎯 第二阶段：修复后的核心锚点逻辑
# ================================

@dataclass
class AnchorPoint:
    """数据锚点数据类"""
    id: str
    name: str
    business_area: str
    address: str
    floor_level: str = ""
    store_number: str = ""
    coordinate: str = ""
    brand_name: str = ""
    merchant_type: str = ""
    unique_id: str = ""
    confidence: float = 0.0
    raw_data: Dict[str, Any] = None
    
    def __post_init__(self):
        if not self.unique_id:
            # 使用核心字段哈希生成唯一ID
            hash_input = f"{self.name}|{self.business_area}|{self.address}|{self.coordinate}"
            self.unique_id = f"anchor_{hash(hash_input) % 1000000}"
        
        if self.raw_data is None:
            self.raw_data = {}


@dataclass
class MatchResult:
    """匹配置信结果"""
    is_match: bool
    confidence_score: float
    matching_details: Dict[str, float]
    recommendations: List[str]
    alternative_pois: List[UnifiedPoiInterface]


class FixedDataAnchorEnhancer:
    """
    修复版数据锚点增强器
    特点：1) 统一数据接口 2) 完整的错误恢复 3) 容错处理
    """
    
    def __init__(self):
        # 商圈标准化词典
        self.business_area_dict = {
            '国贸': ['国贸', 'CBD', '建国门外', '东三环中路'],
            '三里屯': ['三里屯', '工体北路', '三里屯路', '太古里'],
            '王府井': ['王府井', '王府井大街'],
            '中关村': ['中关村', '知春路', '海淀大街'],
            '朝阳公园': ['朝阳公园', '公园南路'],
            '望京': ['望京', '望京街']
        }
        
        # 品牌标准化词典
        self.brand_mappings = {
            'starbucks': '星巴克',
            'kfc': '肯德基',
            'mcdonald': '麦当劳',
            'costa': '咖世家',
            'subway': '赛百味'
        }
        
        # 相似度阈值
        self.thresholds = {
            'name_similarity': 0.85,
            'area_similarity': 0.80, 
            'address_similarity': 0.75,
            'coordinate_distance': 500,
            'comprehensive_score': 0.70
        }
    
    async def create_anchor_from_poi(self, poi_data: Any) -> AnchorPoint:
        """从POI创建数据锚点 - 支持任意数据格式"""
        try:
            # 🎯 统一数据适配
            unified_data = DataAdapter.to_unified(poi_data)
            
            if not DataAdapter.validate_unified(unified_data):
                raise ValueError(f"数据不完整: {getattr(unified_data, 'id', 'unknown')}")
            
            # 🎯 数据提取与标准化
            processed_data = await self._extract_and_normalize(unified_data)
            
            # 🎯 创建锚点
            anchor = AnchorPoint(
                id=getattr(unified_data, 'id', ''),
                name=processed_data['normalized_name'],
                business_area=processed_data['normalized_area'],
                address=processed_data['normalized_address'],
                floor_level=processed_data['floor_info'],
                store_number=processed_data['store_number'],
                coordinate=unified_data.location,
                brand_name=processed_data['brand_name'],
                merchant_type=unified_data.type,
                confidence=processed_data['confidence'],
                raw_data=unified_data.__dict__ if hasattr(unified_data, '__dict__') else {}
            )
            
            logger.debug(f"✅ 锚点创建成功: {anchor.unique_id} | 置信度: {anchor.confidence}")
            return anchor
            
        except Exception as e:
            logger.error(f"❌ 锚点创建失败: {e}")
            # 🎯 故障降级 - 返回基础锚点
            return self._create_fallback_anchor(poi_data, str(e))
    
    async def _extract_and_normalize(self, data: UnifiedPoiInterface) -> Dict[str, Any]:
        """提取和标准化数据"""
        # 名称标准化
        normalized_name = self._normalize_merchant_name(data.name)
        
        # 商圈标准化
        normalized_area = self._normalize_business_area(data.business_area)
        
        # 地址解析
        floor_info = self._extract_floor_info(data.address)
        store_number = self._extract_store_number(data.address) 
        
        # 品牌提取
        brand_name = self._extract_brand_name(data.name)
        
        # 地址标准化
        normalized_address = self._normalize_address(data.address)
        
        # 计算置信度
        confidence = self._calculate_confidence(
            data.name, normalized_name,
            data.business_area, normalized_area,
            brand_name
        )
        
        return {
            'normalized_name': normalized_name,
            'normalized_area': normalized_area,
            'normalized_address': normalized_address,
            'floor_info': floor_info,
            'store_number': store_number,
            'brand_name': brand_name,
            'confidence': confidence
        }
    
    def _normalize_merchant_name(self, name: str) -> str:
        """标准化商家名称"""
        name = (name or '').strip()
        name = re.sub(r'\s*[（\(].*?[）\)]\s*', '', name)  # 移除括号
        name = re.sub(r'\s+(店|餐厅|咖啡店|酒店)\s*$', '', name)  # 移除后缀
        return name.strip()
    
    def _normalize_business_area(self, area: str) -> str:
        """标准化商圈"""
        area = (area or '').strip()
        
        for standard_area, variants in self.business_area_dict.items():
            if area in variants or any(variant in area for variant in variants):
                return standard_area
        
        return area
    
    def _extract_floor_info(self, address: str) -> str:
        """提取楼层信息"""
        address = address or ''
        floor_patterns = [r'(\d+)[层Ff]', r'[Bb](\d+)']
        
        for pattern in floor_patterns:
            match = re.search(pattern, address)
            if match:
                return match.group(0)
        return ""
    
    def _extract_store_number(self, address: str) -> str:
        """提取门牌号"""
        address = address or ''
        number_pattern = r'(\d+)[号-]'
        match = re.search(number_pattern, address)
        
        return match.group(0) if match else ""
    
    def _extract_brand_name(self, merchant_name: str) -> str:
        """提取品牌名"""
        merchant_name = (merchant_name or '').lower()
        
        for brand_key, brand_zh in self.brand_mappings.items():
            if brand_key in merchant_name or brand_zh in merchant_name:
                return brand_zh
        
        # 提取括号中的信息
        import re
        bracket_match = re.search(r'[（\(]([^）\)]+)[）\)]', merchant_name)
        if bracket_match:
            return bracket_match.group(1)
        
        return ""
    
    def _normalize_address(self, address: str) -> str:
        """标准化地址"""
        if not address:
            return ""
        
        address = re.sub(r'\s+', ' ', address)
        address = address.strip('。,，.')
        return address
    
    def _calculate_confidence(self, 
                            original_name: str, normalized_name: str,
                            original_area: str, normalized_area: str,
                            brand_name: str) -> float:
        """计算置信度"""
        base_confidence = 0.7
        
        # 品牌匹配加分
        brand_bonus = 0.2 if brand_name else 0.0
        
        # 商圈标准化加分
        area_bonus = 0.1 if original_area != normalized_area else 0.0
        
        return min(1.0, base_confidence + brand_bonus + area_bonus)
    
    def _create_fallback_anchor(self, original_data: Any, error_msg: str) -> AnchorPoint:
        """创建故障降级锚点"""
        logger.warning(f"创建降级锚点: {error_msg}")
        
        try:
            # 尝试获取基本信息
            fallback_id = getattr(original_data, 'id', '') or original_data.get('id', '') or 'unknown'
            fallback_name = getattr(original_data, 'name', '') or original_data.get('name', '') or '未知商家'
            
            return AnchorPoint(
                id=fallback_id,
                name=fallback_name,
                business_area='未知商圈',
                address='未知地址',
                confidence=0.3,  # 低置信度
                raw_data={'error': error_msg, 'fallback': True}
            )
        except Exception:
            # 完全失败时返回最终降级
            return AnchorPoint(
                id='emergency_fallback',
                name='系统错误',
                business_area='unknown',
                address='unknown',
                confidence=0.1
            )