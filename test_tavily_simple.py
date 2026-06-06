#!/usr/bin/env python3

import aiohttp
import asyncio
import json
import os
from dotenv import load_dotenv

# 先加载.env文件
load_dotenv('.env')
load_dotenv('backend/.env')

# 从环境变量获取API密钥
tavily_api_key = os.getenv('TAVILY_API_KEY')

async def test_tavily_direct():
    """直接用aiohttp测试Tavily连接"""
    print("=== 直接API调用测试 ===")
    print(f"API Key 状态: {'✓ 已配置' if tavily_api_key else '✗ 未配置'}")
    
    if not tavily_api_key:
        print("请先在.env文件中配置TAVILY_API_KEY")
        return
    
    try:
        # 测试参数和你的代码完全一样
        params = {
            "api_key": tavily_api_key,
            "query": "星巴克咖啡 operating hours, current status, is open in 上海大学站",
            "search_depth": "advanced",
            "include_answer": True,
            "include_raw_content": True,
            "max_results": 10
        }
        
        async with aiohttp.ClientSession() as session:
            print("\n正在连接Tavily API...")
            async with session.post(
                "https://api.tavily.com/search", 
                json=params, 
                timeout=5  # 和你的代码一致
            ) as response:
                print(f"HTTP 状态码: {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    print("✅ 连接成功！")
                    print(f"答案: {data.get('answer', '无')[:100]}...")
                    print(f"结果数: {len(data.get('results', []))}")
                else:
                    print(f"❌ 错误: {response.status}")
                    error_text = await response.text()
                    print(f"错误信息: {error_text}")
                
    except asyncio.TimeoutError:
        print("⚠️ 超 timeout 5秒")
    except aiohttp.ClientError as e:
        print(f"🚫 客户端错误: {e}")
    except Exception as e:
        print(f"🔥 未知错误: {e}")

async def test_serper_fallback():
    """测试Serper备选方案"""
    print("\n=== Serper备选测试 ===")
    serper_key = os.getenv('SERPER_API_KEY')
    print(f"Serper Key 状态: {'✓ 已配置' if serper_key else '✗ 未配置'}")
    
    if not serper_key:
        print("跳过Serper测试")
        return
        
    try:
        async with aiohttp.ClientSession() as session:
            params = {
                "q": "星巴克咖啡 上海大学站 site:google.com/maps OR site:yelp.com",
                "gl": "cn",
                "hl": "zh",
                "type": "search"
            }
            headers = {
                "X-API-KEY": serper_key,
                "Content-Type": "application/json"
            }
            
            print("正在连接Serper API...")  
            async with session.post(
                "https://google.serper.dev/search",
                json=params,
                headers=headers,
                timeout=5
            ) as response:
                print(f"HTTP 状态码: {response.status}")
                if response.status == 200:
                    data = await response.json()
                    print("✅ Serper连接成功！")
                    print(f"结果数: {len(data.get('organic', []))}")
                else:
                    error_text = await response.text()
                    print(f"❌ Serper错误: {response.status} - {error_text}")
                    
    except asyncio.TimeoutError:
        print("⚠️ Serper请求超时")
    except Exception as e:
        print(f"🔥 Serper错误: {e}")

async def main():
    await test_tavily_direct()
    await test_serper_fallback()

if __name__ == "__main__":
    asyncio.run(main())