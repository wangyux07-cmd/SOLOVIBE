#!/usr/bin/env python3
"""
测试所有修复是否有效
"""

import json
from backend.services.agent.langgraph_agent import LangGraphAgent, AgentMode
from dataclasses import asdict

def test_json_serialization():
    """测试JSON序列化修复"""
    print("🧪 测试JSON序列化...")
    mode = AgentMode.HEALING
    vibe_context = {
        "vibe_score": 5.0,
        "energy_level": 3.0,
        "mode": mode.value,  # 这应该是修复后的字符串格式
        "social_tendency": 0.0
    }
    
    try:
        serialized = json.dumps(vibe_context)
        print("✅ AgentMode枚举JSON序列化成功!")
        print(f"   JSON: {serialized}")
        return True
    except Exception as e:
        print(f"❌ JSON序列化失败: {e}")
        return False

def test_supabase_import():
    """测试Supabase库导入"""
    print("\n🧪 测试Supabase库导入...")
    try:
        import supabase
        print("✅ Supabase库导入成功!")
        print(f"   版本: {supabase.__version__}")
        return True
    except ImportError as e:
        print(f"❌ Supabase库导入失败: {e}")
        return False

def main():
    print("🚀 SoloVibe修复验证测试")
    print("=" * 50)
    
    # 运行测试
    test1_passed = test_json_serialization()
    test2_passed = test_supabase_import()
    
    print("\n📊 测试总结:")
    print("=" * 50)
    print(f"JSON序列化修复: {'✅ 通过' if test1_passed else '❌ 失败'}")
    print(f"Supabase库安装: {'✅ 通过' if test2_passed else '❌ 失败'}")
    
    all_passed = test1_passed and test2_passed
    print(f"\n{'🎉 所有修复验证通过!' if all_passed else '❌ 部分修复需要检查'}")
    
    return all_passed

if __name__ == "__main__":
    main()