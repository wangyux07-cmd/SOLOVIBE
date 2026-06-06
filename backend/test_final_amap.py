from services.tools.booking_execution_tool import PlaywrightBookingExecutionTool
import asyncio
import os
from dotenv import load_dotenv

# 先加载环境变量
load_dotenv('.env')

async def test():
    print("=== 高德API最终测试 ===")
    tool = PlaywrightBookingExecutionTool()
    
    # 测试几个地址
    test_addresses = ["上海大学站", "三里屯", "北京天安门"]
    
    for address in test_addresses:
        print(f"\n测试地址: {address}")
        result = await tool.get_location_by_query(address)
        if result and 'lat' in result and 'lng' in result:
            print(f"✓ 成功: {result}")
        else:
            print(f"✗ 失败: {result}")

if __name__ == "__main__":
    asyncio.run(test())