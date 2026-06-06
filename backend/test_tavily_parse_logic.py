from services.tools.web_search_tool import WebSearchTool, SearchQuery, BusinessInfo
import asyncio
import os
from dotenv import load_dotenv

load_dotenv('.env')

async def debug_tavily_logic():
    print("=== 调试Tavily解析逻辑 ===")
    
    # 模拟真实的Tavily API响应数据格式
    mock_tavily_response = {
        'answer': '星巴克咖啡在上海大学站附近是营业状态，正常开放',
        'results': [
            {
                'title': '星巴克咖啡(上大路店)',
                'content': '营业时间：7:00-22:00，评分：4.5分，最新评价很好',
                'url': 'https://example.com/starbucks'
            }
        ],
        'query': 'operating hours, current status, is open 星巴克咖啡 in 上海大学站',
        'response_time': 1.2
    }
    
    tool = WebSearchTool()
    
    # 测试解析逻辑
    query = SearchQuery(
        query="星巴克咖啡",
        location="上海大学站", 
        search_type="business_status"
    )
    
    print("模拟Tavily响应:")
    print(f"Answer: {mock_tavily_response['answer']}")
    print(f"Results: {len(mock_tavily_response['results'])} 条")
    
    # 直接调用解析方法
    parsed_result = tool._parse_tavily_response(mock_tavily_response, query)
    
    print("\n解析结果:")
    print(f"✅ 商家名称: {parsed_result.merchant_name}")
    print(f"✅ 地址: {parsed_result.address}") 
    print(f"✅ 是否营业: {parsed_result.is_open}")
    print(f"✅ 营业状态: {parsed_result.current_status}")
    print(f"✅ 评分: {parsed_result.rating}")
    print(f"✅ 评价: {len(parsed_result.recent_reviews) if parsed_result.recent_reviews else 0} 条")
    
    # 查看最近的评价内容
    if parsed_result.recent_reviews:
        print("\n📢 评价详情:")
        for i, review in enumerate(parsed_result.recent_reviews):
            print(f"  评价{i+1}: {review}")
            
    # 测试空的response情况
    print("\n=== 测试空Response情况 ===")
    empty_response = {
        'answer': '',
        'results': [],
        'query': 'test',
        'response_time': 0
    }
    
    empty_result = tool._parse_tavily_response(empty_response, query)
    print(f"空响应解析 - 营业状态: {empty_result.current_status}")
    print(f"空响应解析 - 评分: {empty_result.rating}")

if __name__ == "__main__":
    asyncio.run(debug_tavily_logic())