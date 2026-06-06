from services.tools.booking_execution_tool import PlaywrightBookingExecutionTool
import asyncio
import os
from dotenv import load_dotenv

# 先加载环境变量
load_dotenv('.env')

async def test():
    print("测试高德API调用...")
    print("环境变量检查:", os.getenv('AMAP_API_KEY'))
    
    tool = PlaywrightBookingExecutionTool()
    print("工具初始化后的amap_key:", tool.amap_key)
    
    result = await tool.get_location_by_query('上海大学站')
    print('高德API测试结果:', result)

if __name__ == "__main__":
    asyncio.run(test())