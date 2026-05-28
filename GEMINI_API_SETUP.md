# 🤖 Gemini API 配置指南

SoloVibe 后端使用了 Google Gemini 3.5 Flash 模型来为用户提供个性化的独处建议。以下是配置步骤：

## 🔑 获取 Gemini API Key

### 步骤 1: 访问 Google AI Studio
打开浏览器访问: [https://makersuite.google.com/app/apikey](https://makersuite.google.com/app/apikey)

### 步骤 2: 创建 API Key
1. 使用你的Google账号登录
2. 点击 "Create API key" 按钮
3. 选择 "Create API key in new project"
4. 复制生成的API key

### 步骤 3: 配置文件

将你的API key填入 `backend/.env` 文件中：

```bash
# 复制示例配置文件（如果不存在）
cp backend/.env.example backend/.env
```

编辑 `backend/.env` 文件，找到并修改以下行：

```bash
# === Gemini AI 配置 ===
GEMINI_API_KEY=your-gemini-api-key-here
```

将 `your-gemini-api-key-here` 替换为你刚复制的API key：

```bash
GEMINI_API_KEY=AIzaSyB...你的完整API密钥
```

### 步骤 4: 验证配置

启动后端服务进行测试：

```bash
# 进入后端目录
cd backend

# 安装依赖
pip install -r requirements.txt

# 启动服务
python main.py
```

在服务启动日志中检查是否显示：
```
INFO:GeminiLLMManager:Gemini LLM 管理器初始化完成
```

## 🛡️ 安全提示

- **不要**将API密钥提交到代码仓库
- **不要**与他人分享API密钥  
- 在不需要时及时在Google AI Studio禁用API密钥
- .env 文件已加入到 .gitignore 中

## 🚨 如果API不可用

如果未配置Gemini API密钥，系统会自动降级到**模拟模式**：

- 会显示警告：`"Gemini API key 未配置，将使用模拟模式"`
- 使用预设的友好回复继续提供服务
- 用户可以正常测试系统功能

## 💡 费用说明

Gemini API 采用按使用量计费：
- 新用户有免费的额度可以使用
- 具体费用可在 Google AI Studio 的控制台查看
- Flash 模型性价比高，适合聊天场景

## 🔗 相关链接

- [Google AI Studio](https://makersuite.google.com/)
- [Gemini API 文档](https://ai.google.dev/docs)
- [API Key 管理](https://console.cloud.google.com/apis/credentials)
