from services.tools.web_search_tool import WebSearchTool, SearchQuery
import asyncio
import os
from dotenv import load_dotenv

load_dotenv('.env')

async def debug_search_flow_step_by_step():
    print("=== 深度调试Tavily搜索流程 ===")
    
    async with WebSearchTool() as search_tool:
        query = SearchQuery(
            query="星巴克咖啡",
            location="上海大学站",
            search_type="business_status"
        )
        
        print(f"\n调试查询: {query.query} in {query.location}")
        
        # 步骤1: 检查缓存
        cache_key = search_tool._get_cache_key(query)
        print(f"缓存键: {cache_key}")
        cached_result = search_tool._check_cache(cache_key)
        print(f"缓存检查结果: {'有缓存数据' if cached_result else '无缓存数据'}")
        
        if cached_result:
            print(f"缓存数据状态: {cached_result.current_status}")
            return cached_result
        
        # 步骤2: 尝试Tavily搜索
        print("\n步骤2: 调用Tavily API...")
        try:
            tavily_result = await search_tool._search_tavily(query)
            print(f"Tavily搜索结果: {'成功' if tavily_result else '失败'}")
            if tavily_result:
                print(f"Tavily返回状态: {tavily_result.current_status}")
                return tavily_result
        except Exception as e:
            print(f"Tavily搜索异常: {e}")
            tavily_result = None
        
        # 步骤3: 尝试备选引擎 (Serper)
        print("\n步骤3: 尝试Serper API...")
        serper_result = None
        if search_tool.serper_api_key:
            try:
                serper_result = await search_tool._search_serper(query)
                print(f"Serper搜索结果: {'成功' if serper_result else '失败'}")
                if serper_result:
                    print(f"Serper返回状态: {serper_result.current_status}")
            except Exception as e:
                print(f"Serper搜索异常: {e}")
                serper_result = None
        else:
            print("未配置Serper API")
        
        # 步骤4: fallback到缓存模拟数据
        print("\n步骤4: 使用缓存fallback...")
        fallback_result = await search_tool._search_cache_fallback(query)
        print(f"Fallback数据状态: {fallback_result.current_status}")
        
        # 检查哪一个结果被返回
        if tavily_result:
            print("🔍 最终返回: Tavily结果")
            return tavily_result
        elif serper_result:
            print("🔍 最终返回: Serper结果")
            return serper_result
        else:
            print("🔍 最终返回: Fallback结果")
            return fallback_result

if __name__ == "__main__":
    result = asyncio.run(debug_search_flow_step_by_step())
    print(f"\n=== 最终结果 ===")
    print(f"商家: {result.merchant_name}")
    print(f"状态: {result.current_status}")
    print(f"是否营业: {result.is_open}")
    print(f"评分: {result.rating}")
    
    # 判断数据来源
    if "cached" in result.current_status:
        print("📊 数据来源: 缓存fallback")
    else:
        print("📊 数据来源: 真实API响应")