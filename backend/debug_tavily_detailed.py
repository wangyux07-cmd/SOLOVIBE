from services.tools.web_search_tool import WebSearchTool, SearchQuery
import asyncio
import os
from dotenv import load_dotenv

# 先加载环境变量
load_dotenv('.env')

async def test():
    print("=== Tavily 详细搜索结果分析 ===")
    
    try:
        async with WebSearchTool() as search_tool:
            query = SearchQuery(
                query="上海大学站附近安静角落1",
                location="上海大学站",
                search_type="business_status"
            )
            
            print(f"搜索查询: {query.query} in {query.location}")
            print(f"搜索类型: {query.search_type}")
            print("\n调用API...")
            
            result = await search_tool.search_business_info(query)
            
            if result:
                print("\n=== 实际返回结果 ===")
                print(f"商家名称: {result.merchant_name}")
                print(f"地址: {result.address}")
                print(f"是否营业: {result.is_open}")
                print(f"当前状态: {result.current_status}")
                print(f"最后更新时间: {result.last_updated}")
                print(f"评分: {result.rating}")
                print(f"评价数量: {result.review_count}")
                print(f"最近评价: {result.recent_reviews}")
                print(f"紧急通知: {result.emergency_notices}")
                print(f"高峰时间: {result.peak_hours}")
                print(f"特殊优惠: {result.special_offers}")
                print(f"安全信息: {result.safety_info}")
                
                # 检查哪些字段是空的
                print("\n=== 空字段检查 ===")
                from dataclasses import fields
                for field in fields(result):
                    value = getattr(result, field.name)
                    if value is None or (isinstance(value, (list, str)) and len(value) == 0):
                        print(f"❌ {field.name}: 为空")
                    else:
                        print(f"✅ {field.name}: {value}")
                        
            else:
                print("✗ Tavily搜索返回空结果")
                
    except Exception as e:
        print(f"✗ Tavily搜索异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())