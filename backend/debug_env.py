import os
from dotenv import load_dotenv

# 尝试多种加载方法
print("=== 环境变量调试 ===")

# 检查当前目录
print(f"当前工作目录: {os.getcwd()}")
print(f"__file__ 目录: {os.path.dirname(__file__)}")

# 检查.env文件是否存在
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
print(f".env文件路径: {dotenv_path}")
print(f".env文件存在: {os.path.exists(dotenv_path)}")

# 尝试加载
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
    print(f"从 {dotenv_path} 加载环境变量")
else:
    load_dotenv()
    print("从默认位置加载环境变量")

# 检查环境变量
print(f"\n环境变量检查结果:")
print(f"AMAP_API_KEY: {os.getenv('AMAP_API_KEY', '未设置')}")
print(f"AMAP_BASE_URL: {os.getenv('AMAP_BASE_URL', '未设置')}")
print(f"TAVILY_API_KEY: {os.getenv('TAVILY_API_KEY', '未设置')}")

# 列出所有环境变量中以AMAP_开头的
print(f"\n所有AMAP相关环境变量:")
for key, value in os.environ.items():
    if key.startswith('AMAP'):
        print(f"  {key}: {value}")