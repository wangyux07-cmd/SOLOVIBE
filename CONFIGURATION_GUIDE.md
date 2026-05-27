# 🎯 SoloVibe 配置完整指南

## 📋 配置概览

SoloVibe项目包含后端和前端两部分，每部分都有相应的环境配置。本指南将帮助你完成所有必要的配置步骤。

### 配置文件和路径

```
SOLOVIBE/
├── backend/
│   ├── .env.example          # 后端环境变量模板
│   ├── ENVIRONMENT_SETUP.md   # 后端详细配置指南
│   ├── setup_env.py          # 后端配置助手
│   ├── install_dependencies.bat  # Windows依赖安装
│   ├── install_dependencies.sh   # macOS/Linux依赖安装
│   └── requirements.txt      # 后端依赖列表
│
├── frontend/
│   ├── .env.example          # 前端环境变量模板
│   └── package.json          # 前端依赖配置
│
└── CONFIGURATION_GUIDE.md    # 本文件 - 完整配置指南
```

## 🚀 快速开始

### Windows用户
```bash
cd SOLOVIBE/backend
call install_dependencies.bat
python setup_env.py
```

### macOS/Linux用户
```bash
cd SOLOVIBE/backend
chmod +x install_dependencies.sh
./install_dependencies.sh
python setup_env.py
```

## 🛠️ 后端配置指南

### 步骤1: 创建环境文件

```bash
cd SOLOVIBE/backend
cp .env.example .env
```

### 步骤2: 编辑环境变量

使用任意编辑器打开 `.env` 文件，填写以下必要配置：

#### 📍 必须配置项

```env
# Supabase 数据库配置
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xxxxx

# Web搜索API（二选一即可）
TAVILY_API_KEY=tvly-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# 或
SERPER_API_KEY=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

#### 🗺️ 必须配置项

```env
# 高德地图API（核心服务）
AMAP_API_KEY=your-gaode-api-key
AMAP_BASE_URL=https://restapi.amap.com
```

> **架构说明**：高德地图Web服务API现在是SoloVibe的唯一空间地理服务平台，提供：
> - POI周边深度搜索（咖啡厅、餐厅、公园等）
> - 多模式路径规划（步行、驾车、公交）
> - 地理围栏服务和距离计算

### 步骤3: 验证配置

```bash
python setup_env.py
```

这个脚本会检查所有必要的配置并提供详细的设置说明。

### 步骤4: API密钥获取指南

#### 🔗 Supabase
1. 访问 https://supabase.com
2. 创建账户并新建项目
3. 在项目设置 → API 中找到：
   - Project URL (SUPABASE_URL)
   - anon public key (SUPABASE_KEY)

#### 🔍 Tavily API（推荐）
1. 访问 https://tavily.com
2. 用邮箱注册开发者账户
3. 在Dashboard获取API Key
4. 免费额度：1000次搜索/月

#### 🗺️ 高德地图API
1. 访问 https://lbs.amap.com
2. 注册开发者账号
3. 创建应用获取Key
4. 免费额度：50000次/天

#### 💡 架构说明
- **Tavily API**：专用于情感疗愈内容检索，绝不返回商户信息
- **高德API**：空间地理服务的唯一提供者，包括POI搜索和路径规划
- **开发模式**：可使用 `MOCK_EXTERNAL_APIS=true` 进行功能验证

#### 🎯 职能分离机制
- 情感内容查询 → Tavily（全网心理疗愈内容）
- 地理空间查询 → 高德（POI召回+路径规划）
- LangGraph内将实现智能路由分发

## 🎨 前端配置指南

### 步骤1: 创建前端环境文件

```bash
cd SOLOVIBE/frontend
cp .env.example .env
```

### 步骤2: 配置API端点

```env
# 后端API地址
VITE_API_BASE_URL=http://localhost:8000

# API端点路径
VITE_STREAM_CHAT_ENDPOINT=/api/v1/stream_chat
VITE_HEALTH_CHECK_ENDPOINT=/api/v1/health
VITE_CONFIG_STATUS_ENDPOINT=/api/v1/config-status
```

### 步骤3: 安装前端依赖

```bash
npm install
# 或
yarn install
# 或
pnpm install
```

## 🔍 配置验证和调试

### 后端配置验证

```bash
cd SOLOVIBE/backend

# 方法1: 使用配置助手
python setup_env.py

# 方法2: 启动服务验证
python main.py

# 方法3: 使用API端点
curl http://localhost:8000/api/v1/health
```

### 前端配置验证

```bash
cd SOLOVIBE/frontend

# 启动开发服务器
npm run dev
# 或
yarn dev

# 检查浏览器控制台是否有错误
```

### 常见配置问题

#### 1. 后端启动失败
```
❌ 错误: ModuleNotFoundError: No module named 'xxx'
→ 解决方案: 确保运行了 install_dependencies 脚本
```

#### 2. 数据库连接失败
```
❌ 错误: Connection refused 或 Invalid API key
→ 解决方案: 
   1. 检查 SUPABASE_URL 和 SUPABASE_KEY
   2. 确保Supabase项目已正确配置
   3. 检查网络连接
```

#### 3. Web搜索API失败
```
❌ 错误: API key invalid 或 Quota exceeded
→ 解决方案:
   1. 确认API密钥是否正确
   2. 检查API服务商账户余额
   3. 考虑使用备选API服务
```

#### 4. CORS错误
```
❌ 错误: CORS policy blocked request
→ 解决方案:
   1. 检查 ALLOWED_ORIGINS 配置
   2. 确保前端地址在后端允许的origin列表中
   3. 开发环境可临时设置 ALLOWED_ORIGINS=*
```

## 🔒 安全最佳实践

### 环境文件安全

1. **不要提交敏感信息**
   ```bash
   # 添加到 .gitignore
   .env
   *.key
   *.pem
   ```

2. **使用不同的环境**
   ```env
   # 开发环境
   DEBUG=true
   MOCK_EXTERNAL_APIS=true
   
   # 生产环境
   DEBUG=false
   CSRF_ENABLED=true
   SECRET_KEY=your-very-long-secret-key
   ```

3. **定期轮换密钥**
   ```bash
   # 定期检查和更新API密钥
   git log --oneline .env  # 检查是否有敏感信息泄露
   ```

### 生产环境配置

```env
# backend/.env (生产环境)
DEBUG=false
CSRF_ENABLED=true
SECRET_KEY=your-production-secret-key-here-change-in-production
ALLOWED_ORIGINS=https://your-production-domain.com
LOG_LEVEL=WARNING

# 详细配置...
```

```env
# frontend/.env (生产环境)
VITE_DEBUG=false
VITE_STRICT_CONTENT_SECURITY=true
VITE_LOG_LEVEL=error
VITE_API_BASE_URL=https://api.your-production-domain.com
```

## 📱 平台特定配置

### Windows

```batch
@echo off
:: Windows批处理环境变量设置
set SUPABASE_URL=https://your-project.supabase.co
set SUPABASE_KEY=your-key-here
set TAVILY_API_KEY=your-tavily-key
python main.py
```

### macOS/Linux

```bash
#!/bin/bash
# macOS/Linux环境变量设置
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_KEY="your-key-here"
export TAVILY_API_KEY="your-tavily-key"
python main.py
```

### Docker环境

```bash
# docker-compose.yml 环境变量
environment:
  - SUPABASE_URL=${SUPABASE_URL}
  - SUPABASE_KEY=${SUPABASE_KEY}
  - TAVILY_API_KEY=${TAVILY_API_KEY}
```

## 📊 监控配置状态

### 后端健康检查
访问以下端点查看配置状态：
- `GET /api/v1/health` - 完整健康检查
- `GET /api/v1/config-status` - 配置详情（开发环境）
- `GET /` - 基础状态

### 前端配置调试

```javascript
// 检查环境变量
console.log('API URL:', import.meta.env.VITE_API_BASE_URL);

// 测试API连接
fetch('/api/v1/health')
  .then(response => response.json())
  .then(data => console.log('后端状态:', data));
```

## 🚨 故障排除

### Q: 如何确认配置已正确加载？
A: 运行 `python setup_env.py` 或使用API端点 `/api/v1/config-status` 查看配置状态。

### Q: API调用超限怎么办？
A: 1) 检查账单余额 2) 降低调用频率 3) 考虑升级账户 4) 联系API供应商

### Q: 数据库连接超时怎么办？
A: 1) 检查网络连接 2) 验证数据库URL和密码 3) 检查防火墙设置 4) 尝试使用内网IP

### Q: 如何重置所有配置？
A: 删除 `.env` 文件，重新复制 `.env.example` 并重新配置。

### Q: 配置更改后没生效怎么办？
A: 重启应用程序，环境变量更改需要重新启动才能生效。

## 📞 寻求帮助

如果配置过程中遇到问题：

1. **查看日志文件**：检查控制台输出和日志信息
2. **阅读API文档**：查阅各个API服务的官方文档
3. **配置指南**：参考本目录下的详细文档
4. **代码注释**：查看相关文件中的注释说明

---

🎉 恭喜！按照本指南完成配置后，你的SoloVibe项目应该已经可以正常工作了！

**下一步**：
1. 运行后端服务：`python main.py`
2. 启动前端开发：`npm run dev`
3. 访问 http://localhost:5173 体验完整功能

如有问题，请先检查 `.env` 文件配置，确保所有必需的API密钥都已正确填写。