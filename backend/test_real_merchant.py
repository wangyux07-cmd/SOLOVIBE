from services.tools.web_search_tool import WebSearchTool, SearchQuery
import asyncio
import os
from dotenv import load_dotenv

load_dotenv('.env')

async def test_real_merchants():
    print("=== 使用真实商家名称测试 ===")
    
    # 真实存在的商家名称
    real_merchants = [
        # 上海地区的真实商家
        {"name": "星巴克咖啡", "location": "上海大学站"},
        {"name": "肯德基", "location": "上海大学"},
        {"name": "麦当劳", "location": "上海大学"},
        # 北京的知名商家
        {"name": "故宫博物院", "location": "天安门"},
        {"name": "全聚德烤鸭", "location": "王府井"},
    ]
    
    async with WebSearchTool() as search_tool:
        for merchant in real_merchants:
            print(f"\n--- 测试: {merchant['name']} ---")
            
            query = SearchQuery(
                query=merchant['name'],
                location=merchant['location'],
                search_type="business_status"
            )
            
            result = await search_tool.search_business_info(query)
            
            if result:
                print(f"✅ 成功获取信息:")
                print(f"   商家: {result.merchant_name}")
                print(f"   地址: {result.address}")
                print(f"   营业状态: {result.is_open} ({result.current_status})")
                print(f"   评分: {result.rating}")
                
                # 如果评分等信息不为空，显示详细信息
                if result.rating:
                    print(f"   🔥 获得了真实评分数据!")
                if result.recent_reviews:
                    print(f"   🔥 获得了评价数据: {len(result.recent_reviews)} 条")
                    
                # 检查是否是缓存数据
                if "cached" in result.current_status:
                    print(f"   💡 注意: 这是缓存/模拟数据")
                else:
                    print(f"   🎉 这是真实API数据!")
            else:
                print(f"❌ 获取失败")

if __name__ == "__main__":
    asyncio.run(test_real_merchants())