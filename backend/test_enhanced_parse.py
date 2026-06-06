from services.tools.web_search_tool import WebSearchTool, SearchQuery, BusinessInfo
import asyncio
import os
from dotenv import load_dotenv

load_dotenv('.env')

async def test_enhanced_parsing():
    print("=== 测试增强的Tavily解析逻辑 ===")
    
    # 包含详细信息的模拟响应
    rich_tavily_response = {
        'answer': '星巴克咖啡在上海大学站附近评分4.5分，已有128条用户评价，营业时间7:00-22:00，正常开放',
        'results': [
            {
                'title': '星巴克咖啡(上大路店)',
                'content': '商家评分4.5分，共128条评价，营业时间：周一至周日 7:00-22:00',
                'url': 'https://maps.google.com/starbucks'
            },
            {
                'title': '用户最新评价',
                'content': '环境很好，服务员态度友善，咖啡品质不错，值得推荐',
                'url': 'https://reviews.example.com/1'
            }
        ],
        'query': 'operating hours, current status, is open 星巴克咖啡 in 上海大学站',
        'response_time': 1.2
    }
    
    tool = WebSearchTool()
    
    query = SearchQuery(
        query="星巴克咖啡",
        location="上海大学站", 
        search_type="business_status"
    )
    
    print("模拟丰富的Tavily响应:")
    print(f"Answer: {rich_tavily_response['answer']}")
    print(f"Results: {len(rich_tavily_response['results'])} 条")
    for i, result in enumerate(rich_tavily_response['results']):
        print(f"  结果{i+1}: {result['content']}")
    
    # 测试增强的解析方法
    parsed_result = tool._parse_tavily_response(rich_tavily_response, query)
    
    print("\n=== 增强解析结果 ===")
    print(f"✅ 商家名称: {parsed_result.merchant_name}")
    print(f"✅ 地址: {parsed_result.address}") 
    print(f"✅ 是否营业: {parsed_result.is_open}")
    print(f"✅ 营业状态: {parsed_result.current_status}")
    print(f"✅ 评分: {parsed_result.rating}")  # 应该能提取到4.5
    print(f"✅ 评价数量: {parsed_result.review_count}")  # 应该能提取到128
    print(f"✅ 最近评价: {len(parsed_result.recent_reviews)} 条")
    
    # 查看具体提取的评分和评价数
    if parsed_result.rating:
        print(f"🎯 成功提取评分: {parsed_result.rating}分")
    if parsed_result.review_count:
        print(f"🎯 成功提取评价数量: {parsed_result.review_count}条")
        
    print("\n=== 单独测试评分提取 ===")
    test_texts = [
        "评分4.5分，环境不错",
        "用户评分：4.2，共89条评价", 
        "这家店铺5分好评如潮",
        "综合评分3.8/5",
        "⭐4.0星评价",
        "没有任何评分信息"
    ]
    
    for text in test_texts:
        rating = tool._extract_rating_from_text(text, [])
        review_count = tool._extract_review_count_from_text(text, [])
        print(f"'{text}' -> 评分:{rating}, 数量:{review_count}")

if __name__ == "__main__":
    asyncio.run(test_enhanced_parsing())