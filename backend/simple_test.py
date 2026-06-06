import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv('.env')

# 测试环境变量
print('AMAP_API_KEY:', os.getenv('AMAP_API_KEY'))
print('是否为空:', not os.getenv('AMAP_API_KEY'))
print('是否以your-开头:', os.getenv('AMAP_API_KEY', '').startswith('your-'))