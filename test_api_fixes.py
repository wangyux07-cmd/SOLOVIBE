#!/usr/bin/env python3
"""
API修复验证测试脚本
验证Tavily和高德API调用是否正常工作
"""

import asyncio
import os
import sys
from pathlib import Path

# 添加backend到Python路径
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

# 首先加载环境变量
from dotenv import load_dotenv
load_dotenv(backend_path / ".env")

from services.tools.web_search_tool import WebSearchTool, SearchQuery
from services.tools.booking_execution_tool import PlaywrightBookingExecutionTool

def print_env_status():
    """打印环境变量状态"""
    print("\n" + "="*60)
    print("环境变量配置状态")
    print("="*60)
    
    tavily_key = os.getenv("TAVILY_API_KEY")
    amap_key = os.getenv("AMAP_API_KEY")
    amap_url = os.getenv("AMAP_BASE_URL")
    
    print(f"TAVILY_API_KEY: {'✓ 已配置' if tavily_key and not tavily_key.startswith('your-') else '✗ 未配置'}")
    print(f"AMAP_API_KEY: {'✓ 已配置' if amap_key and not amap_key.startswith('your-') else '✗ 未配置'}")
    print(f"AMAP_BASE_URL: {amap_url or '使用默认值'}")
    print(f"WEB_SEARCH_TIMEOUT: {os.getenv('WEB_SEARCH_TIMEOUT', '15')}秒")
    print("="*60 + "\n")

async def test_tavily_search():
    """测试Tavily搜索"""
    print("\n🔍 测试Tavily Web搜索...")
    
    if not os.getenv("TAVILY_API_KEY"):
        print("⚠️  TAVILY_API_KEY未配置，跳过Tavily测试")
        return
    
    try:
        async with WebSearchTool() as search_tool:
            query = SearchQuery(
                query="上海大学站附近安静角落",
                location="上海大学站",
                search_type="business_status"
            )
            
            result = await search_tool.search_business_info(query)
            
            if result:
                print(f"✓ Tavily搜索成功: {result.merchant_name}")
                print(f"  状态: {result.current_status}")
                print(f"  地址: {result.address}")
            else:
                print("✗ Tavily搜索返回空结果")
                
    except Exception as e:
        print(f"✗ Tavily搜索失败: {e}")

async def test_amap_geocoding():
    """测试高德地理编码"""
    print("\n🗺️  测试高德地理编码...")
    
    if not os.getenv("AMAP_API_KEY"):
        print("⚠️  AMAP_API_KEY未配置，跳过高德API测试")
        return
    
    try:
        tool = PlaywrightBookingExecutionTool()
        
        # 测试地址
        test_address = "上海大学站"
        result = await tool.get_location_by_query(test_address)
        
        if result and 'lat' in result and 'lng' in result:
            print(f"✓ 高德地理编码成功: {test_address}")
            print(f"  经度: {result['lng']}")
            print(f"  纬度: {result['lat']}")
        else:
            print("✗ 高德地理编码失败或无结果")
            
    except Exception as e:
        print(f"✗ 高德地理编码异常: {e}")

def test_env_loading():
    """测试环境变量加载"""
    print("\n📁 环境变量加载测试...")
    
    # 检查各种可能的.env文件位置
    possible_paths = [
        backend_path / ".env",
        Path(".env"),
        Path("backend/.env")
    ]
    
    for path in possible_paths:
        if path.exists():
            print(f"✓ 找到.env文件: {path}")
            return
    
    print("✗ 未找到任何.env配置文件")
    print("可能的文件位置:")
    for path in possible_paths:
        print(f"  - {path}")

async def main():
    """主测试函数"""
    print("🚀 开始API修复验证测试")
    
    # 打印当前环境状态
    test_env_loading()
    print_env_status()
    
    # 检查必要的依赖
    try:
        import aiohttp
        print("✓ aiohttp已安装")
    except ImportError:
        print("✗ aiohttp未安装")
        return
    
    # 运行测试
    await test_tavily_search()
    await test_amap_geocoding()
    
    print("\n🎯 测试完成!")
    print("\n如果测试失败，请检查:")
    print("1. .env文件中的API密钥是否正确")
    print("2. 网络连接是否正常")
    print("3. API服务提供商的状态")
    print("4. 防火墙设置")

if __name__ == "__main__":
    asyncio.run(main())