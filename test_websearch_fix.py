#!/usr/bin/env python3
"""
测试WebSearchTool修复
"""
import asyncio
import sys
import os

project_root = os.path.dirname(os.path.abspath(__file__))
backend_path = os.path.join(project_root, "backend")
sys.path.insert(0, backend_path)

async def test_web_search_tool():
    """测试WebSearchTool是否正常工作"""
    try:
        from services.tools.web_search_tool import WebSearchTool
        from services.agent.langgraph_agent import SearchQuery
        
        print("测试WebSearchTool...")
        
        # 使用async context manager
        async with WebSearchTool() as search_tool:
            query = SearchQuery(
                query="上海大学站附近安静的酒吧",
                location="上海大学站",
                search_type="business_status"
            )
            
            result = await search_tool.search_business_info(query)
            
            if result:
                print(f"✅ WebSearchTool成功! 商家: {result.name}, 状态: {result.current_status}")
                print(f"  是否有具体对象: {type(result)}, 属性: {dir(result)}")
                return True
            else:
                print("❌ WebSearchTool返回None")
                return False
                
    except Exception as e:
        print(f"❌ WebSearchTool测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_batch_retrieval():
    """测试批量实时检索"""
    try:
        os.chdir(os.path.join(project_root, "backend"))
        from services.agent.langgraph_agent import LangGraphAgentNode
        
        print("\n测试批量实时检索...")
        
        agent = LangGraphAgentNode()
        
        # 测试计划列表
        plans = [
            {"merchant_name": "大学路静吧", "merchant_address": "上海大学站"},
            {"merchant_name": "安静咖啡厅", "merchant_address": "上海大学站"},
        ]
        
        location_info = {"lat": 31.32, "lng": 121.39, "address": "上海大学站"}
        user_message = "心情不好想喝酒"
        
        enhanced_plans = await agent._batch_real_time_info_retrieval(plans, location_info, user_message)
        
        if enhanced_plans and len(enhanced_plans) > 0:
            print(f"✅ 批量检索成功! 处理了{len(enhanced_plans)}个商家")
            for i, plan in enumerate(enhanced_plans):
                print(f"  商家{i+1}: {plan.get('merchant_name', '未知')}, 实时状态: {plan.get('real_time_status', '无')}")
            return True
        else:
            print("❌ 批量检索失败")
            return False
            
    except Exception as e:
        print(f"❌ 批量检索测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    print("开始WebSearchTool修复验证...")
    
    result1 = await test_web_search_tool()
    result2 = await test_batch_retrieval()
    
    if result1 and result2:
        print("\n✅ 所有测试通过！")
        return True
    else:
        print("\n❌ 测试失败")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
