# 🛠️ 环境变量配置指南

## 📋 配置文件说明

SoloVibe后端需要正确配置环境变量才能正常运行。主要配置文件为 `.env`，您可以基于 `.env.example` 模板创建。

### 快速开始

```bash
# 复制示例配置文件
cp .env.example .env

# 编辑配置
nano .env  # 或在您喜欢的编辑器中打开

# 启动应用
python main.py
```

## 🔑 必填配置项

### 1. Supabase 数据库配置

**获取方式**：
1. 访问 [supabase.com](https://supabase.com) 并注册/登录
2. 创建新项目
3. 在项目设置中找到：
   - **API** → `Project URL`（SUPABASE_URL）
   - **API** → `anon` key（SUPABASE_KEY）

```env
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xxxxx
```

### 2. Web 搜索 API 配置（情感疗愈内容专用）

#### 选项一：Tavily API（推荐）

**获取方式**：
1. 访问 [tavily.com](https://tavily.com) 
2. 注册开发者账户
3. 在控制台获取API密钥

```env
TAVILY_API_KEY=tvly-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

#### 选项二：Serper API（备选）

**获取方式**：
1. 访问 [serper.dev](https://serper.dev)
2. 注册账户获取API密钥

```env
SERPER_API_KEY=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

**费用说明**：
- Tavily：$10/月，包含1000次搜索
- Serper：$0.50/1000次搜索
- 两者都有免费额度，初期开发够用

### 3. 高德地图 Web 服务 API（POI检索+路径规划统一平台）

> **🏛️ 架构变革**：高德地图API现在是SoloVibe的唯一空间地理服务平台

#### 高德地图API（核心服务）

**统一职能范围**：
- ✅ POI周边深度搜索（咖啡厅、餐厅、公园、书店等）
- ✅ 多模式路径规划（步行、驾车、公交换乘）  
- ✅ 地理编码/逆地理编码
- ✅ 地理围栏服务
- ✅ 距离计算和可达性分析

**❌ 不再支持**：
- ~~美团API（餐厅预订）~~ **已弃用，完全迁移到高德地图API**
- 滴滴API（打车出行）
- 所有地理空间服务已统一迁移到高德

**获取方式**：
1. 访问 [高德开放平台](https://lbs.amap.com)
2. 注册账号
3. 创建应用获取Key

```env
AMAP_API_KEY=your_amap_key_here
AMAP_BASE_URL=https://restapi.amap.com
```

**费用说明**：
- 每天50000次免费额度
- 需要实名认证手机号
- 超出免费额度后按需计费

## ⚙️ 可选配置项

### 调试和性能

```env
# 开发模式（开启详细日志）
DEBUG=true
DEV_MODE=true

# 日志级别
LOG_LEVEL=INFO  # 可选: DEBUG, INFO, WARNING, ERROR

# Mock模式（不调用真实API，使用模拟数据）
MOCK_EXTERNAL_APIS=false
```

### 安全和性能优化

```env
# 生产环境安全配置
CSRF_ENABLED=true
SECRET_KEY=your-very-long-secret-key-change-this-in-production

# API超时设置
WEB_SEARCH_TIMEOUT=5          # Web搜索超时（秒）
BOOKING_EXECUTION_TIMEOUT=30  # 预订执行超时（秒）

# 流控设置（每秒请求数）
TAVILY_RATE_LIMIT=10
# 高德API流量控制
AMAP_RATE_LIMIT=20
```

### 风控阈值

```env
# 风险评估阈值
COST_RISK_THRESHOLD_MEDIUM=80   # 费用中等风险阈值（元）
COST_RISK_THRESHOLD_HIGH=200    # 费用高风险阈值（元）
DURATION_RISK_THRESHOLD_MEDIUM=120  # 时长中等风险阈值（分钟）
DURATION_RISK_THRESHOLD_HIGH=360    # 时长高风险阈值（分钟）
```

## 🧪 开发环境建议配置

对于本地开发，建议使用以下配置：

```env
# === 基础配置 ===
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key

# === API配置（可先使用Mock模式） ===
MOCK_EXTERNAL_APIS=true
DEV_MODE=true

# 基础搜索API（选择一个即可）
TAVILY_API_KEY=tvly-demo-key  # 申请实际的密钥

# === 开发优化 ===
DEBUG=true
LOG_LEVEL=DEBUG
WEB_SEARCH_TIMEOUT=10  # 开发时可以给更长时间

# === 前端配置 ===
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
```

## 🚀 生产环境推荐配置

生产环境需要更严格的安全设置：

```env
# === 生产安全配置 ===
DEBUG=false
DEV_MODE=false
CSRF_ENABLED=true
SECRET_KEY=your-production-secret-key-very-long-and-random

# === 性能优化 ===
LOG_LEVEL=WARNING
WEB_SEARCH_TIMEOUT=3
BOOKING_EXECUTION_TIMEOUT=15

# === 监控配置 ===
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=8001

# === 生产API配置 ===
# 确保使用生产环境的API密钥
TAVILY_API_KEY=your-production-tavily-key
# MEITUAN_API_KEY=your-production-meituan-key  # 已废弃，不再使用
AMAP_API_KEY=your-production-gaode-key

# === 安全限制 ===
ALLOWED_ORIGINS=https://your-production-domain.com
MAX_UPLOAD_SIZE=5242880  # 5MB
```

## ⚠️ 重要安全提醒

1. **不要提交敏感信息**：确保 `.env` 文件被添加到 `.gitignore`
   ```bash
   echo ".env" >> .gitignore
   ```

2. **环境隔离**：开发、测试、生产环境使用不同的密钥

3. **定期rotation**：定期更新API密钥和SECRET_KEY

4. **最小权限原则**：只申请必要的API权限

## 🔍 配置验证脚本

创建验证脚本确保配置正确：

```python
# check_config.py
import os
import sys

def check_env_variables():
    required_vars = [
        'SUPABASE_URL',
        'SUPABASE_KEY',
        'TAVILY_API_KEY'  # 至少需要一种搜索API
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ 缺少必要环境变量:")
        for var in missing_vars:
            print(f"   - {var}")
        sys.exit(1)
    
    print("✅ 所有必要环境变量已配置")

if __name__ == "__main__":
    check_env_variables()
```

运行验证：
```bash
python check_config.py
```

## 💡 获取API密钥的技巧

### Tavily API
- 访问 https://tavily.com
- 使用个人邮箱注册（可使用Gmail）
- 立即获得免费额度（1000次搜索/月）
- 支持信用卡付款升级

### 高德地图API
- 访问 https://lbs.amap.com
- 个人开发者可以申请
- 每天50000次免费额度
- 需要实名认证手机号

### ~~美团API~~ （**已弃用**）
- 主要针对企业开发者
- 个人开发者可使用Mock模式开发
- 或者寻找合作伙伴获取企业资质

### 替代方案
如果API获取困难，可以先使用Mock模式开发完整功能，后续接入真实API。

## 📞 问题支持

如果配置文件有任何问题：
1. 检查 `.env` 文件格式是否正确
2. 确保所有密钥都是实际申请的，不是示例值
3. 查看应用启动日志获取具体错误信息
4. 验证网络连接和防火墙设置

现在您可以根据这个指南来配置所有必要的API密钥和环境变量了！🚀