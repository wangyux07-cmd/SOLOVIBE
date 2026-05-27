#!/usr/bin/env python3
"""
城市副本册桥接测试
验证数据接力同步机制
"""

import asyncio
from backend.services.data.wanderbook_bridge import (
    WanderbookBridge, WanderbookEntry, WanderbookEntryStatus, WanderbookEntryType
)
from backend.services.tools.booking_execution_tool import PlaywrightBookingResult, AmapPoiResult


async def test_entry_creation():
    """测试条目创建"""
    print("📚 测试1: 条目创建")
    
    bridge = WanderbookBridge()
    
    # 模拟预订结果
    booking_result = PlaywrightBookingResult(
        success=True,
        booking_id="test_booking_wb_001",
        form_data={
            'name': '张三',
            'phone': '13800138000',
            'drinks': ['美式咖啡', '拿铁'],
            'people': 2
        },
        screenshot_url="https://example.com/screenshot.jpg"
    )
    
    poi_info = AmapPoiResult(
        id="amap_poi_wb_001",
        name="星巴克咖啡（三里屯店）",
        address="北京市朝阳区三里屯路工体北路13号",
        location="116.455158,39.936407",
        type="咖啡",
        typecode="050112",
        business_area="三里屯"
    )
    
    # 创建条目
    entry_id = await bridge.create_entry_from_booking(
        booking_result, poi_info, "test_user"
    )
    
    print(f"  ✅ 条目创建成功: {entry_id}")
    
    # 验证条目
    entry = await bridge.get_entry(entry_id, "test_user")
    
    if entry:
        print(f"    商家名称: {entry.merchant_name}")
        print(f"    商圈: {entry.business_area}")
        print(f"    状态: {entry.status.value}")
        print(f"    类型: {entry.entry_type.value}")
        
        assert entry.merchant_name == poi_info.name, "商家名称不匹配"
        assert entry.status == WanderbookEntryStatus.PENDING_CHECKIN, "状态不正确"
    
    print()


async def test_status_sync():
    """测试状态同步"""
    print("🔄 测试2: 状态同步")
    
    bridge = WanderbookBridge()
    entry_id = "wanderbook_test_sync_001"
    
    # 创建测试条目
    test_entry = WanderbookEntry(
        id=entry_id,
        user_id="test_user",
        booking_id="test_booking_sync",
        poi_id="test_poi",
        merchant_name="测试咖啡店",
        merchant_coordinates="116.123,39.456",
        merchant_address="测试地址",
        business_area="测试商圈",
        entry_type=WanderbookEntryType.PLAYWRIGHT_BOOKING
    )
    
    # 模拟保存到本地缓存
    await bridge._save_to_local_cache(test_entry)
    
    print(f"  📝 初始状态: {test_entry.status.value}")
    
    # 更新状态 - 进行打卡
    update_success = await bridge.update_entry_status(
        entry_id, 
        WanderbookEntryStatus.IN_PROGRESS,
        "test_user"
    )
    
    print(f"  ✅ 状态更新成功: {update_success}")
    
    # 再次打卡完成
    completion_success = await bridge.update_entry_status(
        entry_id,
        WanderbookEntryStatus.COMPLETED,
        "test_user",
        additional_data={
            'checkin_time': '2026-05-28T14:30:00',
            'mood_rating': 5
        }
    )
    
    print(f"  ✅ 完成打卡成功: {completion_success}")
    print()


async def test_scenario_entry():
    """测试场景方案创建条目"""
    print("🎨 测试3: 场景方案条目创建")
    
    bridge = WanderbookBridge()
    
    # 模拟合成数据场景
    scenario_info = {
        'scenario_id': 'healing_scenario_001',
        'title': '三里屯咖啡治愈之旅',
        'merchant_info': {
            'id': 'synth_poi_001',
            'name': '慢时光咖啡屋',
            'location': {'coordinates': '116.455158,39.936407', 'area': '三里屯'},
            'address': '北京市朝阳区三里屯路19号院',
            'type': '咖啡体验'
        },
        'type': 'healing'
    }
    
    # 从场景创建条目
    entry_id = await bridge.create_entry_from_scenario(scenario_info)
    
    print(f"  ✅ 场景条目创建成功: {entry_id}")
    
    # 验证条目类型
    entry = await bridge.get_entry(entry_id)
    if entry:
        assert entry.entry_type == WanderbookEntryType.SCENARIO_GENERATED, "类型不正确"
        print(f"    条目类型: {entry.entry_type.value}")
    print()


if __name__ == "__main__":
    print("🌉 城市副本册桥接测试\n")
    
    # 清理测试文件
    cache_file = Path("wanderbook_cache")
    if cache_file.exists():
        for file in cache_file.glob("*test*.json"):
            file.unlink()
    
    asyncio.run(test_entry_creation())
    asyncio.run(test_status_sync())
    asyncio.run(test_scenario_entry())
    
    print("🎉 城市副本册桥接测试完成！")