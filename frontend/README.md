# SoloVibe Frontend

🧘‍♀️ 专为独处设计的 React 前端应用，支持 Gemini 2.5 Pro 模型集成

## 技术栈

- **Framework**: React 18 + TypeScript
- **Build Tool**: Vite 5
- **Styling**: Tailwind CSS
- **HTTP Client**: 原生 Fetch API + Streaming 支持
- **LLM**: Gemini 2.5 Pro 集成

## 核心特性

- 🤖 **Gemini 2.5 Pro 驱动** - 自适应情商机制的对话体验
- 🔄 **流式 SSE 传输** - 逐字响应和混合推送
- ✨ **响应式设计** - Mobile First 的绝佳体验
- 🧠 **自适应感知** - 动态调节对话风格
- 🗺️ **地图导航** - 发现独处好去处

## 快速开始

### 前置要求

- Node.js 18+
- supabase 项目 (用于存储消息历史)
- Google Gemini API 密钥

### 安装依赖

```bash
cd frontend
npm install
```

### 配置环境变量

复制示例文件并填入你的配置：

```bash
cp .env.example .env
```

然后编辑 `.env` 文件，填入你的 API 地址：

```
VITE_API_BASE_URL=http://localhost:8000
```

### 开发服务器

```bash
npm run dev
```

应用将在 [http://localhost:5173](http://localhost:5173) 上启动

### 构建生产版本

```bash
npm run build
npm run preview
```

## API 集成

### SSE 流式对话

- **端点**: `/api/gemini/stream`
- **方法**: POST
- **内容类型**: application/json
- **响应**: text/plain (SSE 格式)

### 示例请求

```ts
const request = {
  message: "你好",
  thread_id: "current-thread-id",
  energy_level: "high",
  continue_thread: false
};

// 使用 fetch 获取流式响应
const headers = { 
  'Content-Type': 'application/json',
  'X-API-Key': 'your-key'
};

const response = await fetch(`/api/gemini/stream`, { 
  method: 'POST', 
  headers, 
  body: JSON.stringify(request)
});
```

### 类型定义

```ts
interface StreamChatRequest {
  message: string;
  thread_id: string;
  energy_level: 'low' | 'medium' | 'high';
  continue_thread: boolean;
  reset?: boolean;
}

interface StreamChatResponse {
  content: string;
  type: 'content' | 'planning' | 'error';
  thread_id: string;
  event_type?: 'word' | 'sentence' | 'mixed';
}
```

## 项目结构

```
src/
├── components/         	# React 组件
│   ├── StreamChatDemo.tsx	# 流式聊天演示
│   └── MapPage.tsx      	# 地图页面
├── hooks/              	# 自定义 Hooks
│   └── useSoloStream.ts 	# SSE 封装
├── types/              	# TypeScript 类型
│   └── api.ts         	# API 接口定义
├── App.tsx            	# 主应用
├── main.tsx          	# 入口文件
└── index.css         	# 全局样式
```

## 关键组件说明

### StreamChatDemo
核心聊天组件，包含：
- 消息输入框
- 历史消息展示
- SSE 流式显示区域
- 积极混合推送功能（思维泡泡）

### MapPage
地图组件，展示：
- 建议的独处地点
- 位置标记和描述
- 模拟的地图界面

### useSoloStream Hook
SSE 封装，提供：
- 连接池管理
- 重连机制
- 断线检测
- 数据处理

## 状态管理

### 对话状态

```ts
interface ChatState {
  thread_id: string;
  messages: Message[];
  energyLevel: EnergyEnum;
  isStreaming: boolean;
  status: ThreadStatus;
}
```

### 地图状态

```ts
interface MapState {
  selectedPin: MapInstancePin | null;
  currentLocation: { lat: number; lng: number };
  nearbySpots: Array<{ name: string; distance: string }>;
}
```

## CORS 配置

确保后端配置正确的 CORS：

```ts
// 在 FastAPI 后端中
app.add_middleware(
  CORSMiddleware,
  allow_origins=["http://localhost:5173"],
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)
```

## 常见问题

### Q: 如何配置 API 密钥？
A: 在请求头中添加 `X-API-Key`，或在后端通过环境变量设置。

### Q: SSE 连接不稳定怎么办？
A: `useSoloStream` 会自动处理重连，你也可以在组件中实现自定义的重连逻辑。

### Q: 如何在其他组件中使用地图数据？
A: 通过 `MapInstancePin` 类型定义接口，将数据作为 props 传递给子组件。

## 性能优化

### 1. 虚拟滚动
对长列表组件启用虚拟滚动，优化渲染性能。

### 2. 服务 Worker
考虑添加 PWA 支持，提升离线体验。

### 3. 代码分割
通过 `React.lazy` 和 `Suspense` 实现路由级代码分割。

## 测试

使用 Jest 和 React Testing Library 编写单元测试：

```bash
npm run test
```

## 许可证

MIT License

## 贡献

欢迎提交 Issues 和 Pull Requests 来改进这个项目。