import asyncio
import sys
import os

project_root = os.path.dirname(os.path.abspath(__file__))
backend_path = os.path.join(project_root, "backend")
sys.path.insert(0, backend_path)

async def debug_step1_init():
    """调试WebSearchTool初始化"""
    try:
        from services.tools.web_search_tool import WebSearchTool
        
        print("✅ WebSearchTool模块导入成功")
        
        # 测试直接初始化
        tool = WebSearchTool()
        print(f"   session属性: {tool.session}")
        print(f"   属性列表: {dir(tool)}")
        
        # 测试async context manager
        async with tool as search_tool:
            print(f"   在context manager内 session: {search_tool.session}")
            print(f"   session类型: {type(search_tool.session)}")
            
        return True
    except Exception as e:
        print(f"❌ WebSearchTool初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def debug_step2_search():
    """调试搜索"""
    try:
        from services.tools.web_search_tool import WebSearchTool
        from services.agent.langgraph_agent import SearchQuery
        
        print("\n测试搜索功能:")
        
        # 先检查API key
        import os
        tavily_key = os.getenv("TAVILY_API_KEY")
        print(f"Tavily API Key: {'已配置' if tavily_key else '未配置'}")
        
        async with WebSearchTool() as tool:
            # 模拟cache fallback情况
            query = SearchQuery(
                query="上海大学站附近安静的酒吧", 
                location="上海大学站",
                search_type="business_status"
            )
            
            # 直接检查cache
            cache_key = tool._get_cache_key(query)
            print(f"缓存键: {cache_key}")
            
            # 从cache获取
            result = await tool._search_cache_fallback(query)
            print(f"缓存结果: {result}")
            
            return True
            
    except Exception as e:
        print(f"❌ 搜索功能失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    print("调试WebSearchTool...")
    
    step1 = await debug_step1_init()
    step2 = await debug_step2_search()
    
    if step1 and step2:
        print("\n✅ WebSearchTool调试通过")
    else:
        print("\n❌ WebSearchTool调试失败")

if __name__ == "__main__":
    asyncio.run(main())
