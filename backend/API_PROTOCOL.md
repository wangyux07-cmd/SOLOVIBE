# SoloVibe 通信协议规范

## 1. SSE 标签化流协议

### 响应标签定义
- `[EMPATHY]`: 同理心反馈，包含文本内容
- `[PLANS]`: 计划JSON数据
- `[REQUIRE_USER_CONFIRM]`: 触发HITL中断确认，前端必须暂停执行等待用户确认

### 数据格式示例
```
data: [EMPATHY] 理解您现在的心情，让我为您规划一下...

event: message
data: [PLANS] {"id": "plan-1", "title": "独自咖啡时光", "duration": "2小时"}

event: interrupt
data: [REQUIRE_USER_CONFIRM]
```

## 2. API 接口定义

### POST /api/v1/stream_chat
接收客户端消息并启动流式响应

**请求体:**
```json
{
  "message": "我想找个地方独自待会儿",
  "thread_id": "session-123456"
}
```

**响应:**
- Content-Type: text/event-stream
- 流式返回标签化数据

## 3. 状态持久化规范

### Thread 状态定义
- `active`: 正常对话状态
- `waiting_confirmation`: 等待用户确认状态
- `completed`: 对话完成

### Supabase 表结构
- `threads`: 存储对话状态和元数据
- `messages`: 存储具体消息内容
- `checkpoints`: LangGraph检查点数据
