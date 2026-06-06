from services.tools.web_search_tool import WebSearchTool, SearchQuery
import asyncio
import os
from dotenv import load_dotenv

# 先加载环境变量
load_dotenv('.env')

async def test():
    print("=== Tavily API最终测试 ===")
    
    try:
        async with WebSearchTool() as search_tool:
            query = SearchQuery(
                query="上海大学站附近安静角落",
                location="上海大学站",
                search_type="business_status"
            )
            
            print(f"搜索查询: {query.query} in {query.location}")
            result = await search_tool.search_business_info(query)
            
            if result:
                print(f"✓ Tavily搜索成功: {result.merchant_name}")
                print(f"  状态: {result.current_status}")
                print(f"  地址: {result.address}")
                print(f"  是否营业: {result.is_open}")
            else:
                print("✗ Tavily搜索返回空结果")
                
    except Exception as e:
        print(f"✗ Tavily搜索异常: {e}")

if __name__ == "__main__":
    asyncio.run(test())