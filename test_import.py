#!/usr/bin/env python3
"""
简单测试LangGraphAgent是否能正常导入
"""

import sys
import os

# 添加backend目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

try:
    from backend.services.agent.langgraph_agent import LangGraphAgent
    print("✅ LangGraphAgent导入成功")
    
    # 测试初始化
    agent = LangGraphAgent()
    print("✅ LangGraphAgent初始化成功")
    
except Exception as e:
    print(f"❌ 导入或初始化失败: {e}")
    import traceback
    traceback.print_exc()