#!/usr/bin/env python3
"""
数据锚点增强器测试
验证同名店铺精准匹配能力
"""

import asyncio

# Mock AmapPoiResult to avoid import issues
class MockAmapPoiResult:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

# Import after defining mock
from backend.services.data.data_anchor_enhancer import DataAnchorEnhancer, AnchorPoint, SimpleAmapPoiResult


async def test_anchor_creation():
    """测试锚点创建"""
    print("🧪 测试1: 锚点创建")
    
    enhancer = DataAnchorEnhancer()
    
    # 创建测试POI数据
    test_poi = SimpleAmapPoiResult(
        id="amap_001",
        name="星巴克咖啡（三里屯店）",
        address="北京市朝阳区三里屯路工体北路13号",
        location="116.455158,39.936407",
        type="咖啡",
        typecode="050112",
        business_area="三里屯",
        rating="4.8"
    )
    
    # 创建锚点
    anchor = await enhancer.create_anchor_from_poi(test_poi)
    
    print(f"✅ 锚点创建成功:")
    print(f"  名称: {anchor.name}")
    print(f"  商圈: {anchor.business_area}") 
    print(f"  地址: {anchor.address}")
    print(f"  坐标: {anchor.coordinate}")
    print(f"  品牌: {anchor.brand_name}")
    print(f"  置信度: {anchor.confidence}")
    
    assert anchor.brand_name == "星巴克", "品牌提取失败"
    assert anchor.confidence >= 0.9, "置信度过低"
    print()


async def test_poi_matching():
    """测试POI匹配置信"""
    print("🧪 测试2: 同名店铺区分")
    
    enhancer = DataAnchorEnhancer()
    
    # 三里屯星巴克（目标）
    target_poi = SimpleAmapPoiResult(
        id="target_001",
        name="星巴克咖啡（三里屯店）", 
        address="北京市朝阳区三里屯路工体北路13号",
        location="116.455158,39.936407",
        type="咖啡",
        typecode="050112",
        business_area="三里屯"
    )
    
    # 候选POI列表（包含同名混淆店铺）
    candidates = [
        SimpleAmapPoiResult(
            id="candidate_001",
            name="星巴克咖啡（朝阳公园店）",
            address="北京市朝阳区朝阳公园南路15号",
            location="116.483223,39.937512",
            type="咖啡", 
            typecode="050112",
            business_area="朝阳公园"
        ),
        SimpleAmapPoiResult(
            id="candidate_002",
            name="星巴克咖啡（三里屯太古里店）",
            address="北京市朝阳区三里屯路19号院太古里P1-10号",
            location="116.455890,39.937123",
            type="咖啡",
            typecode="050112", 
            business_area="三里屯"
        )
    ]
    
    # 匹配置信
    match_result = await enhancer.match_poi_with_anchors(target_poi, candidates)
    
    print(f"✅ 匹配置信结果:")
    print(f"  是否匹配: {match_result.is_match}")
    print(f"  置信度: {match_result.confidence_score:.2f}")
    print(f"  详情: {match_result.matching_details}")
    print(f"  建议: {match_result.recommendations}")
    
    if match_result.alternative_pois:
        print(f"  最佳匹配: {match_result.alternative_pois[0].name}")
        print(f"  商圈: {match_result.alternative_pois[0].business_area}")
    
    assert match_result.alternative_pois, "无候选匹配"
    print()


async def test_validation():
    """测试匹配置信验证"""
    print("🧪 测试3: 匹配结果验证")
    
    enhancer = DataAnchorEnhancer()
    
    # 目标POI（三里屯星巴克）
    target_poi = SimpleAmapPoiResult(
        id="target_001",
        name="星巴克咖啡（三里屯店）",
        address="北京市朝阳区三里屯路工体北路13号",
        location="116.455158,39.936407",
        type="咖啡",
        typecode="050112",
        business_area="三里屯"
    )
    
    # 实际选择POI（三里屯太古里店）
    selected_poi = SimpleAmapPoiResult(
        id="selected_001", 
        name="星巴克咖啡（三里屯太古里店）",
        address="北京市朝阳区三里屯路19号院太古里P1-10号",
        location="116.455890,39.937123",
        type="咖啡",
        typecode="050112",
        business_area="三里屯"
    )
    
    # 验证匹配
    is_valid, confidence, corrections = await enhancer.validate_and_correct_match(
        target_poi, selected_poi
    )
    
    print(f"✅ 验证结果:")
    print(f"  有效性: {is_valid}")
    print(f"  置信度: {confidence:.2f}")
    print(f"  纠正建议: {corrections}")
    
    print()


if __name__ == "__main__":
    print("📍 数据锚点增强器测试\n")
    
    asyncio.run(test_anchor_creation())
    asyncio.run(test_poi_matching())
    asyncio.run(test_validation())
    
    print("🎉 数据锚点测试完成！")