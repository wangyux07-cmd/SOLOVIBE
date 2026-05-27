"""
数据锚点对齐增强器
解决同名店铺混淆问题，实现精准匹配
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, List, Tuple
import logging
from datetime import datetime
import re
from difflib import SequenceMatcher

from ...data_types import AmapPoiResult

logger = logging.getLogger(__name__)

@dataclass
class AnchorPoint:
    """数据锚点数据类"""
    name: str
    business_area: str
    address: str
    floor_level: str = ""  # 楼层信息
    store_number: str = ""  # 门牌号/店铺号
    coordinate: str = ""  # 经纬度
    brand_name: str = ""  # 品牌名（如果适用）
    merchant_type: str = ""  # 商户类型
    unique_id: str = ""  # 唯一标识符
    confidence: float = 0.0  # 匹配置信度
    
    def __post_init__(self):
        if not self.unique_id:
            self.unique_id = f"anchor_{hash(self.name + self.business_area + self.address + self.coordinate) % 1000000}"

@dataclass
class MatchResult:
    """匹配置信结果"""
    is_match: bool
    confidence_score: float
    matching_details: Dict[str, float]
    recommendations: List[str]
    alternative_pois: List[AmapPoiResult]

class DataAnchorEnhancer:
    """数据锚点对齐增强器 - 解决同名店铺混淆"""
    
    def __init__(self):
        # 预处理的商圈词典
        self.business_area_dict = {
            '国贸': ['国贸', 'CBD', '建国门外', '东三环中路'],
            '三里屯': ['三里屯', '工体北路', '三里屯路', '太古里'],
            '王府井': ['王府井', '王府井大街'],
            '中关村': ['中关村', '知春路', '海淀大街'],
            '朝阳公园': ['朝阳公园', '公园南路'],
            '望京': ['望京', '望京街'],
            '亦庄': ['亦庄', '亦庄开发区'],
            '大兴': ['大兴', '大兴新城', '亦庄']
        }
        
        # 品牌标准化词典
        self.brand_mappings = {
            'starbucks': '星巴克',
            'kfc': '肯德基',
            'mcdonald': '麦当劳',
            'costa': '咖世家',
            'dq': '冰雪皇后',
            'subway': '赛百味',
            'pizzahut': '必胜客',
            'haidilao': '海底捞',
            'teastone': '茶太',
            'yifusix': '一夫茶'
        }
        
        # 地址标准化模式
        self.address_patterns = [
            r'(\d+)[层Ff]',  # 楼层
            r'(\d+)[号-]',  # 门牌号
            r'[区|座|栋|单元|室]'  # 建筑分区
        ]
        
        # 相似度阈值
        self.thresholds = {
            'name_similarity': 0.85,
            'area_similarity': 0.80,
            'address_similarity': 0.75,
            'coordinate_distance': 500,  # 米
            'comprehensive_score': 0.70
        }
    
    async def create_anchor_from_poi(self, poi: AmapPoiResult) -> AnchorPoint:
        """从POI创建数据锚点"""
        try:
            # 提取坐标
            coordinates = poi.location if poi.location else ""
            
            # 提取品牌名
            brand_name = await self._extract_brand_name(poi.name)
            
            # 提取楼层信息
            floor_level = self._extract_floor_info(poi.address)
            
            # 提取门牌号
            store_number = self._extract_store_number(poi.address)
            
            # 标准化地址
            normalized_address = self._normalize_address(poi.address)
            
            anchor = AnchorPoint(
                name=poi.name.strip(),
                business_area=poi.business_area.strip() if poi.business_area else "",
                address=normalized_address,
                floor_level=floor_level,
                store_number=store_number,
                coordinate=coordinates,
                brand_name=brand_name,
                merchant_type=poi.type if hasattr(poi, 'type') else "",
                confidence=0.95  # 原始POI置信度高
            )
            
            logger.debug(f"创建锚点: {anchor.name} -> {anchor.business_area}")
            
            return anchor
            
        except Exception as e:
            logger.error(f"创建数据锚点失败: {e}")
            raise
    
    async def create_anchor_from_user_input(self, user_input: Dict[str, Any]) -> AnchorPoint:
        """从用户输入创建数据锚点"""
        try:
            # 标准化用户输入
            name = user_input.get('merchant_name', '').strip()
            business_area = user_input.get('business_area', '').strip()
            address = user_input.get('address', '').strip()
            coordinates = user_input.get('coordinates', '')
            
            # 应用标准化
            normalized_name = await self._normalize_merchant_name(name)
            normalized_area = await self._normalize_business_area(business_area)
            
            anchor = AnchorPoint(
                name=normalized_name,
                business_area=normalized_area,
                address=self._normalize_address(address),
                coordinate=coordinates,
                confidence=0.70  # 用户输入置信度相对较低
            )
            
            return anchor
            
        except Exception as e:
            logger.error(f"从用户输入创建锚点失败: {e}")
            raise
    
    async def match_poi_with_anchors(self, 
                                   target_poi: AmapPoiResult,
                                   candidate_pois: List[AmapPoiResult]) -> MatchResult:
        """
        匹配合适的POI，基于多重锚点校验
        """
        if not candidate_pois:
            return MatchResult(
                is_match=False,
                confidence_score=0.0,
                matching_details={},
                recommendations=["无候选商户"],
                alternative_pois=[]
            )
        
        # 为候选POI创建锚点
        anchor_targets = []
        for poi in candidate_pois:
            try:
                anchor = await self.create_anchor_from_poi(poi)
                anchor_targets.append(anchor)
            except Exception:
                continue
        
        if not anchor_targets:
            return MatchResult(
                is_match=False,
                confidence_score=0.0,
                matching_details={},
                recommendations=["无法创建锚点数据"],
                alternative_pois=[]
            )
        
        # 获取目标锚点
        try:
            target_anchor = await self.create_anchor_from_poi(target_poi)
        except Exception:
            target_anchor = None
        
        if not target_anchor:
            # 无法创建目标锚点，使用模糊匹配置信
            return await self._fuzzy_match_pois(target_poi, candidate_pois)
        
        # 执行多层级匹配
        match_scores = []
        for i, candidate_anchor in enumerate(anchor_targets):
            score = await self._calculate_match_score(target_anchor, candidate_anchor)
            match_scores.append((i, score, candidate_pois[i]))
        
        # 排序并获取最佳匹配
        match_scores.sort(key=lambda x: x[1], reverse=True)
        best_match_idx, best_score, best_poi = match_scores[0]
        
        # 判断是否匹配置信
        is_match = best_score >= self.thresholds['comprehensive_score']
        
        # 生成匹配置信详情
        matching_details = await self._generate_matching_details(
            target_anchor, anchor_targets[best_match_idx]
        )
        
        # 生成建议
        recommendations = await self._generate_recommendations(
            is_match, best_score, len(candidate_pois)
        )
        
        # 获取替代选项（前3名）
        alternative_pois = [item[2] for item in match_scores[:3]]
        
        return MatchResult(
            is_match=is_match,
            confidence_score=best_score,
            matching_details=matching_details,
            recommendations=recommendations,
            alternative_pois=alternative_pois
        )
    
    async def validate_and_correct_match(self,
                                      target_poi: AmapPoiResult,
                                      selected_poi: AmapPoiResult) -> Tuple[bool, float, List[str]]:
        """
        验证并纠正匹配结果
        """
        validation_results = []
        
        # 创建锚点
        target_anchor = await self.create_anchor_from_poi(target_poi)
        selected_anchor = await self.create_anchor_from_poi(selected_poi)
        
        # 各项验证
        name_validation = await self._validate_name_match(target_anchor, selected_anchor)
        area_validation = await self._validate_area_match(target_anchor, selected_anchor)
        address_validation = await self._validate_address_match(target_anchor, selected_anchor)
        coordinate_validation = await self._validate_coordinate_proximity(target_anchor, selected_anchor)
        
        validation_results.extend([name_validation, area_validation, address_validation, coordinate_validation])
        
        # 计算整体置信度
        confidence = sum(result['score'] for result in validation_results) / len(validation_results)
        
        # 生成纠正建议
        corrections = await self._generate_correction_suggestions(
            validation_results, target_anchor, selected_anchor
        )
        
        is_valid = confidence >= self.thresholds['comprehensive_score']
        
        return is_valid, confidence, corrections
    
    async def _extract_brand_name(self, merchant_name: str) -> str:
        """从商家名中提取品牌名"""
        merchant_lower = merchant_name.lower()
        
        # 检查品牌词典
        for brand_key, brand_zh in self.brand_mappings.items():
            if brand_key in merchant_lower or brand_zh in merchant_name:
                return brand_zh
        
        # 提取括号中的信息（通常是品牌名或分店信息）
        import re
        bracket_match = re.search(r'[（\(]([^）\)]+)[）\)]', merchant_name)
        if bracket_match:
            return bracket_match.group(1)
        
        return ""
    
    def _extract_floor_info(self, address: str) -> str:
        """提取楼层信息"""
        floor_patterns = [r'(\d+)[层Ff]', r'[Bb](\d+)']
        
        for pattern in floor_patterns:
            match = re.search(pattern, address)
            if match:
                return match.group(0)
        
        return ""
    
    def _extract_store_number(self, address: str) -> str:
        """提取门牌号/店铺号"""
        number_pattern = r'(\d+)[号-]'
        match = re.search(number_pattern, address)
        
        if match:
            return match.group(0)
        
        return ""
    
    async def _normalize_merchant_name(self, name: str) -> str:
        """标准化商家名称"""
        # 移除常见前缀后缀
        name = re.sub(r'\s*[（\(].*?[）\)]\s*', '', name)  # 移除括号内容
        name = re.sub(r'\s+(店|餐厅|咖啡店|酒店|公司|有限公司)\s*$', '', name)
        name = name.strip()
        
        return name
    
    async def _normalize_business_area(self, area: str) -> str:
        """标准化商圈名称"""
        area = area.strip()
        
        # 查找匹配的商圈词典
        for standard_area, variants in self.business_area_dict.items():
            if area in variants or any(variant in area for variant in variants):
                return standard_area
        
        return area
    
    def _normalize_address(self, address: str) -> str:
        """标准化地址"""
        if not address:
            return ""
        
        # 移除多余空格和特殊字符
        address = re.sub(r'\s+', ' ', address)
        address = address.strip('。,，.')
        
        return address
    
    async def _calculate_match_score(self, target: AnchorPoint, candidate: AnchorPoint) -> float:
        """计算两个锚点之间的匹配置信分数"""
        scores = {}
        
        # 名称相似度
        scores['name'] = await self._calculate_name_similarity(target.name, candidate.name)
        
        # 商圈相似度
        scores['area'] = await self._calculate_area_similarity(target.business_area, candidate.business_area)
        
        # 地址相似度
        scores['address'] = await self._calculate_address_similarity(target.address, candidate.address)
        
        # 坐标距离（如果可用）
        if target.coordinate and candidate.coordinate:
            scores['coordinate'] = await self._calculate_coordinate_proximity_score(
                target.coordinate, candidate.coordinate
            )
        else:
            scores['coordinate'] = 0.0
        
        # 品牌和类型匹配
        if target.brand_name and candidate.brand_name:
            scores['brand'] = 1.0 if target.brand_name == candidate.brand_name else 0.0
        elif target.merchant_type and candidate.merchant_type:
            scores['type'] = 1.0 if target.merchant_type == candidate.merchant_type else 0.0
        else:
            scores['brand'] = 0.5  # 默认为中性分
        
        # 加权平均
        weights = {
            'name': 0.3,
            'area': 0.2,
            'address': 0.2,
            'coordinate': 0.15,
            'brand': 0.15
        }
        
        total_score = sum(scores.get(key, 0) * weight for key, weight in weights.items())
        
        logger.debug(f"匹配置信得分: {total_score} (详情: {scores})")
        
        return total_score
    
    async def _calculate_name_similarity(self, name1: str, name2: str) -> float:
        """计算名称相似度"""
        # 标准化名称
        norm_name1 = await self._normalize_merchant_name(name1)
        norm_name2 = await self._normalize_merchant_name(name2)
        
        # 使用SequenceMatcher计算相似度
        similarity = SequenceMatcher(None, norm_name1, norm_name2).ratio()
        
        # 品牌匹配额外加分
        brand1 = await self._extract_brand_name(name1)
        brand2 = await self._extract_brand_name(name2)
        
        if brand1 and brand2 and brand1 == brand2:
            similarity = max(similarity, 0.8)  # 品牌名相同至少0.8分
        
        return similarity
    
    async def _calculate_area_similarity(self, area1: str, area2: str) -> float:
        """计算商圈相似度"""
        norm_area1 = await self._normalize_business_area(area1)
        norm_area2 = await self._normalize_business_area(area2)
        
        if norm_area1 == norm_area2:
            return 1.0
        
        # 部分匹配
        if norm_area1 in norm_area2 or norm_area2 in norm_area1:
            return 0.7
        
        return 0.0
    
    async def _calculate_address_similarity(self, address1: str, address2: str) -> float:
        """计算地址相似度"""
        if not address1 or not address2:
            return 0.0
        
        norm_addr1 = self._normalize_address(address1)
        norm_addr2 = self._normalize_address(address2)
        
        # SequenceMatcher相似度
        similarity = SequenceMatcher(None, norm_addr1, norm_addr2).ratio()
        
        # 检查门牌号是否一致
        num1 = self._extract_store_number(address1)
        num2 = self._extract_store_number(address2)
        
        if num1 and num2 and num1 == num2:
            similarity = max(similarity, 0.8)
        
        return similarity
    
    async def _calculate_coordinate_proximity_score(self, coord1: str, coord2: str) -> float:
        """计算坐标邻近度分数"""
        try:
            # 解析坐标
            lon1, lat1 = map(float, coord1.split(','))
            lon2, lat2 = map(float, coord2.split(','))
            
            # 计算距离（简化版——实际需要Haversine公式）
            distance = abs(lon1 - lon2) + abs(lat1 - lat2)
            distance_meters = distance * 111000  # 简单的度到米转换
            
            # 距离越大分数越低
            if distance_meters <= 100:  # 100米内
                return 1.0
            elif distance_meters <= 500:  # 500米内
                return 0.8
            elif distance_meters <= 1000:  # 1公里内
                return 0.6
            else:
                return max(0.0, 1.0 - distance_meters / 10000)  # 线性衰减
                
        except Exception:
            return 0.0
    
    async def _fuzzy_match_pois(self, target_poi: AmapPoiResult, candidate_pois: List[AmapPoiResult]) -> MatchResult:
        """模糊匹配置信（当无法创建锚点时）"""
        best_matches = []
        
        for candidate in candidate_pois:
            # 简单名称相似度
            name_sim = self._calculate_simple_similarity(target_poi.name, candidate.name)
            
            # 商圈匹配
            area_sim = 1.0 if target_poi.business_area and target_poi.business_area in candidate.business_area else 0.5
            
            # 地址相似度
            addr_sim = 0.0
            if target_poi.address and candidate.address:
                addr_sim = self._calculate_simple_similarity(
                    target_poi.address[:20], candidate.address[:20]  # 比较前20个字符
                )
            
            overall_score = (name_sim * 0.6 + area_sim * 0.2 + addr_sim * 0.2)
            best_matches.append((overall_score, candidate))
        
        best_matches.sort(key=lambda x: x[0], reverse=True)
        
        if best_matches:
            best_score, best_candidate = best_matches[0]
            
            return MatchResult(
                is_match=best_score >= 0.6,
                confidence_score=best_score,
                matching_details={
                    'name_similarity': self._calculate_simple_similarity(target_poi.name, best_candidate.name),
                    'area_match': target_poi.business_area in best_candidate.business_area,
                    'address_similarity': addr_sim
                },
                recommendations=["基于简单匹配模式"],
                alternative_pois=[item[1] for item in best_matches[:3]]
            )
        
        return MatchResult(
            is_match=False, confidence_score=0.0, matching_details={},
            recommendations=["无法找到匹配置信商户"], alternative_pois=[]
        )
    
    def _calculate_simple_similarity(self, text1: str, text2: str) -> float:
        """计算简单文本相似度"""
        return SequenceMatcher(None, text1, text2).ratio()
    
    async def _generate_matching_details(self, target: AnchorPoint, candidate: AnchorPoint) -> Dict[str, float]:
        """生成匹配置信详情"""
        return {
            'name_similarity': await self._calculate_name_similarity(target.name, candidate.name),
            'area_match': 1.0 if await self._normalize_business_area(target.business_area) == await self._normalize_business_area(candidate.business_area) else 0.0,
            'address_similarity': await self._calculate_address_similarity(target.address, candidate.address),
            'brand_match': 1.0 if target.brand_name == candidate.brand_name else 0.0,
            'coordinate_proximity': await self._calculate_coordinate_proximity_score(target.coordinate, candidate.coordinate) if target.coordinate and candidate.coordinate else 0.0
        }
    
    async def _generate_recommendations(self, is_match: bool, score: float, total_candidates: int) -> List[str]:
        """生成建议列表"""
        recommendations = []
        
        if is_match:
            if score >= 0.9:
                recommendations.append("✅ 高度匹配置信 - 可直接执行")
            elif score >= 0.8:
                recommendations.append("✅ 良好匹配 - 建议人工确认")
            else:
                recommendations.append("⚠️ 部分匹配 - 建议二次核实")
        else:
            recommendations.append("❌ 未找到合适匹配")
            
            if total_candidates > 1:
                recommendations.append("🔍 建议检查其他候选商户")
            else:
                recommendations.append("🔄 建议扩大搜索范围")
                
        return recommendations
    
    async def _validate_name_match(self, target: AnchorPoint, candidate: AnchorPoint) -> Dict[str, Any]:
        """验证名称匹配"""
        similarity = await self._calculate_name_similarity(target.name, candidate.name)
        
        return {
            'type': 'name_match',
            'score': similarity,
            'details': {
                'target_name': target.name,
                'candidate_name': candidate.name,
                'similarity': similarity,
                'meets_threshold': similarity >= self.thresholds['name_similarity']
            }
        }
    
    async def _validate_area_match(self, target: AnchorPoint, candidate: AnchorPoint) -> Dict[str, Any]:
        """验证商圈匹配"""
        target_area_normalized = await self._normalize_business_area(target.business_area)
        candidate_area_normalized = await self._normalize_business_area(candidate.business_area)
        
        is_match = target_area_normalized == candidate_area_normalized
        
        return {
            'type': 'area_match',
            'score': 1.0 if is_match else 0.0,
            'details': {
                'target_area': target.business_area,
                'candidate_area': candidate.business_area,
                'normalized_target': target_area_normalized,
                'normalized_candidate': candidate_area_normalized,
                'is_match': is_match
            }
        }
    
    async def _validate_address_match(self, target: AnchorPoint, candidate: AnchorPoint) -> Dict[str, Any]:
        """验证地址匹配"""
        similarity = await self._calculate_address_similarity(target.address, candidate.address)
        
        return {
            'type': 'address_match',
            'score': similarity,
            'details': {
                'target_address': target.address,
                'candidate_address': candidate.address,
                'similarity': similarity,
                'meets_threshold': similarity >= self.thresholds['address_similarity']
            }
        }
    
    async def _validate_coordinate_proximity(self, target: AnchorPoint, candidate: AnchorPoint) -> Dict[str, Any]:
        """验证坐标邻近度"""
        if not target.coordinate or not candidate.coordinate:
            return {
                'type': 'coordinate_proximity',
                'score': 0.0,
                'details': {'has_coordinates': False}
            }
        
        proximity_score = await self._calculate_coordinate_proximity_score(target.coordinate, candidate.coordinate)
        
        return {
            'type': 'coordinate_proximity',
            'score': proximity_score,
            'details': {
                'target_coordinate': target.coordinate,
                'candidate_coordinate': candidate.coordinate,
                'proximity_score': proximity_score
            }
        }
    
    async def _generate_correction_suggestions(self,
                                            validation_results: List[Dict[str, Any]],
                                            target: AnchorPoint,
                                            candidate: AnchorPoint) -> List[str]:
        """生成纠正建议"""
        suggestions = []
        
        for result in validation_results:
            if result['score'] < 0.7:
                issue_type = result['type']
                
                if issue_type == 'name_match':
                    details = result['details']
                    if details['similarity'] < 0.6:
                        suggestions.append(f"🔤 商家名称差异较大：'{details['target_name']}' vs '{details['candidate_name']}'")
                        
                elif issue_type == 'area_match' and not result['details']['is_match']:
                    suggestions.append(f"📍 商圈不一致：'{result['details']['normalized_target']}' vs '{result['details']['normalized_candidate']}'")
                    
                elif issue_type == 'address_match':
                    if result['score'] < 0.5:
                        suggestions.append(f"🏠 地址差异显著：前者'{target.address}'，后者'{candidate.address}'")
                        
                elif issue_type == 'coordinate_proximity':
                    if not result['details']['has_coordinates']:
                        suggestions.append("📍 坐标数据缺失，无法验证距离")
                    elif result['score'] < 0.3:
                        suggestions.append("📍 坐标距离较远")
        
        return suggestions