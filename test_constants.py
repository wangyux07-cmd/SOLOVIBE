"""
测试数据和常量定义
统一管理所有测试用例的核心数据
"""

from typing import Dict, Any

# 📍 测试商户数据
test_merchants = {
    'starbucks_sanlitun': {
        'id': 'amap_sb_sanlitun',
        'name': '星巴克咖啡（三里屯店）',
        'address': '北京市朝阳区三里屯路工体北路13号三层',
        'business_area': '三里屯',
        'location': '116.455158,39.936407',
        'type': '咖啡',
        'typecode': '050112',
        'rating': '4.8',
        'brand': '星巴克'
    },
    'starbucks_chaoyangpark': {
        'id': 'amap_sb_chaoyang',
        'name': '星巴克咖啡（朝阳公园店）',
        'address': '北京市朝阳区朝阳公园南路15号',
        'business_area': '朝阳公园',
        'location': '116.483223,39.937512',
        'type': '咖啡',
        'typecode': '050112',
        'rating': '4.6',
        'brand': '星巴克'
    },
    'local_cafe': {
        'id': 'amap_local_001',
        'name': '慢时光咖啡屋',
        'address': '北京市朝阳区三里屯路23号',
        'business_area': '三里屯',
        'location': '116.456789,39.938123',
        'type': '咖啡',
        'typecode': '050112',
        'rating': '4.5',
        'brand': '独立品牌'
    }
}

# 🛣️ 测试路线数据
test_route = {
    'distance': '1250',
    'duration': '15',
    'taxi_cost': '25',
    'steps': [
        {'instruction': '从当前位置出发', 'distance': '500m', 'action': 'depart'},
        {'instruction': '直行200米', 'distance': '200m', 'action': 'straight'},
        {'instruction': '左转进入工体北路', 'distance': '550m', 'action': 'left_turn'}
    ]
}

# 👤 测试用户数据
test_users = {
    'default_user': {
        'name': '张三',
        'phone': '13800138000',
        'people': 2,
        'preferred_time': '2026-05-28 15:00',
        'location': '北京市朝阳区望京SOHO'
    },
    'solo_user': {
        'name': '李四',
        'phone': '13811111111',
        'people': 1,
        'preferred_time': '2026-05-28 10:30',
        'location': '北京市海淀区中关村'
    }
}

# 🔒 测试阻断场景
test_blocking_scenarios = {
    'slider_captcha': {
        'type': 'slider_captcha',
        'selectors': ['.geetest_slider', '.captcha-slider'],
        'instruction': '请拖动滑块完成验证',
        'expected_strategy': 'request_user_help'
    },
    'sms_verification': {
        'type': 'sms_verification', 
        'selectors': ['.send-sms-btn', '[placeholder*="验证码"]'],
        'instruction': '请输入手机验证码',
        'expected_strategy': 'request_user_help'
    },
    'login_required': {
        'type': 'login_required',
        'selectors': ['.login-popup', '请先登录'],
        'instruction': '请先完成登录',
        'expected_strategy': 'request_user_help'
    },
    'rate_limiting': {
        'type': 'rate_limiting',
        'selectors': ['访问过于频繁', '请稍后再试'],
        'instruction': '操作过于频繁，请等待30秒',
        'expected_strategy': 'delay_retry'
    }
}

# ✅ 预期测试结果
test_expectations = {
    'anchor_creation': {
        'name_extraction': {'星巴克咖啡（三里屯店）': '星巴克'},
        'area_normalization': {'三里屯路': '三里屯', 'CBD国贸': '国贸'},
        'address_parsing': {'三里屯路工体北路13号': {'number': '13号', 'floor': '三层'}},
        'min_confidence': 0.7
    },
    'poi_matching': {
        'same_brand_different_location': 0.3,  # 星巴克三里屯 vs 星巴克朝阳公园
        'same_location_similar_name': 0.8,    # 星巴克三里屯 vs 星巴克三里屯太古里
        'exact_match': 0.95                   # 完全相同
    },
    'wanderbook_creation': {
        'entry_types': ['playwright_booking', 'manual_booking', 'amap_poi_discovery', 'scenario_generated'],
        'status_flow': ['pending_checkin', 'in_progress', 'completed', 'cancelled'],
        'required_fields': ['merchant_name', 'business_area', 'booking_id']
    },
    'full_flow': {
        'max_execution_time': 300,  # 5分钟
        'expected_success_rate': 0.95,
        'acceptable_error_types': ['network_timeout', 'element_not_found']
    }
}

# 🧪 边缘情况测试数据
test_edge_cases = {
    'missing_coordinates': {
        'merchant': '某家小店',
        'address': '北京市某区某街',
        'business_area': '未知',
        'location': ''
    },
    'duplicate_names': [
        test_merchants['starbucks_sanlitun'],
        test_merchants['starbucks_chaoyangpark']
    ],
    'incomplete_address': {
        'name': '小餐馆',
        'address': '',
        'business_area': '三里屯',
        'location': '116.455158,39.936407'
    },
    'very_long_name': {
        'name': '这是一个非常非常长的商家名称测试用例以确保系统能处理超长字符串的情况',
        'address': '北京市朝阳区',
        'business_area': '朝阳区',
        'location': '116.483223,39.937512'
    }
}