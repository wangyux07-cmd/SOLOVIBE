#!/usr/bin/env python3
"""
浏览器状态管理测试
验证快照保存/恢复机制
"""

import asyncio
import json
from pathlib import Path
from backend.services.tools.booking_execution_tool import BrowserStateManager, BrowserContext


async def test_snapshot_save_load():
    """测试快照保存与加载"""
    print("💾 测试1: 浏览器快照")
    
    manager = BrowserStateManager()
    booking_id = "test_booking_001"
    
    # 模拟网页状态数据
    mock_state = {
        'url': 'https://amap.com/booking/test',
        'title': '星巴克咖啡预约',
        'cookies': [{'name': 'session', 'value': 'abc123'}],
        'local_storage': '{"cart": "[]"}',
        'session_storage': '{"temp_data": "xyz"}',
        'form_inputs': '{"name": "张三", "phone": "13800138000"}',
        'booking_id': booking_id,
        'created_at': '2026-05-28T12:00:00',
        'user_agent': 'Mozilla/5.0 Test Browser'
    }
    
    # 保存快照
    snapshot_id = f"{booking_id}_snapshot_test"
    await manager._save_to_local(snapshot_id, mock_state)
    
    print(f"  ✅ 快照保存成功: {snapshot_id}")
    
    # 验证文件存在
    snapshot_file = Path("browser_snapshots") / f"{snapshot_id}.json"
    assert snapshot_file.exists(), "快照文件未创建"
    
    # 加载快照
    loaded_state = await manager._load_from_local(snapshot_id)
    
    print(f"  ✅ 快照加载成功:")
    print(f"    原始URL: {mock_state['url']}")
    print(f"    加载URL: {loaded_state['url']}")
    print(f"    表单数据匹配: {mock_state['form_inputs'] == loaded_state['form_inputs']}")
    
    assert loaded_state['url'] == mock_state['url'], "URL不匹配"
    assert loaded_state['form_inputs'] == mock_state['form_inputs'], "表单数据不匹配"
    print()


async def test_context_restoration():
    """测试上下文恢复流程"""
    print("🔄 测试2: 上下文恢复模拟")
    
    manager = BrowserStateManager()
    booking_id = "test_booking_002"
    
    # 模拟中断前的操作状态
    interruption_state = {
        'current_page': 'payment_confirm',
        'form_filled': True,
        'anti_bot_detected': False,
        'last_action': 'clicked_pay_button'
    }
    
    print(f"  📋 中断状态记录:")
    print(f"    页面: {interruption_state['current_page']}")
    print(f"    表单: {'已完成' if interruption_state['form_filled'] else '未完成'}")
    print(f"    最后动作: {interruption_state['last_action']}")
    
    # 模拟恢复时的下一步指示
    recovery_instructions = [
        "1. 恢复网页到支付确认页面",
        "2. 检查表单数据完整性", 
        "3. 重新加载支付按钮状态",
        "4. 等待用户确认支付"
    ]
    
    print(f"  📋 恢复指示:")
    for i, instruction in enumerate(recovery_instructions, 1):
        print(f"    {instruction}")
    
    print(f"  ✅ 上下文恢复流程测试完成")
    print()


if __name__ == "__main__":
    print("🖥️  浏览器状态管理测试\n")
    
    # 清理旧测试文件
    snapshot_dir = Path("browser_snapshots")
    if snapshot_dir.exists():
        for file in snapshot_dir.glob("*test*.json"):
            file.unlink()
    
    asyncio.run(test_snapshot_save_load())
    asyncio.run(test_context_restoration())
    
    print("🎉 浏览器状态测试完成！")