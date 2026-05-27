import asyncio
import json
import logging
from datetime import datetime
from typing import AsyncGenerator, Dict, Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import uvicorn

from types import (
    StreamChatRequest, StreamChatResponse, ThreadStatus, 
    SSEEventType, StreamResponseType, ThreadState
)
from db.supabase_client import SupabaseClient
from services.agent.langgraph_agent import LangGraphAgent
from middleware.risk_control import verify_action_risk

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="SoloVibe Backend API",
    description="AI-powered solo experience planning with LangGraph and Supabase",
    version="0.1.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize clients
supabase_client = SupabaseClient()
langgraph_agent = LangGraphAgent()


async def stream_chat_handler(message: str, thread_id: str) -> AsyncGenerator[str, None]:
    """
    核心流式聊天处理器，模拟LangGraph工作流并实现HITL中断
    """
    try:
        logger.info(f"开始处理thread_id: {thread_id}, message: {message}")
        
        # 1. 从Supabase恢复或创建thread状态
        thread_state = await supabase_client.get_or_create_thread(thread_id)
        
        # 2. 发送初始同理心回应
        empathy_text = f"我理解您的需求：'{message}'，让我为您规划一下最适合的独享体验..."
        yield f"data: {StreamResponseType.EMPATHY.value} {empathy_text}\n\n"
        
        # 小延迟模拟处理时间
        await asyncio.sleep(1)
        
        # 3. 生成并发送计划
        sample_plan = {
            "id": "wander-plan-001",
            "title": "独自咖啡时光",
            "category": "休闲放松",
            "duration": "2小时",
            "cost": "¥50-80",
            "area": "三里屯",
            "quote": "一个人也要好好生活",
            "highlightTag": "一人友好",
            "subChips": ["安静", "WiFi", "插座"],
            "description": "找到一家温馨的独立咖啡店，享受属于自己的静谧时光",
            "image": "/coffee-shop.jpg"
        }
        
        yield f"data: {StreamResponseType.PLANS.value} {json.dumps(sample_plan, ensure_ascii=False)}\n\n"
        
        await asyncio.sleep(1)
        
        # 4. 触发风控检查 - 核心HITL中断点
        risk_assessment = await verify_action_risk(sample_plan, thread_state)
        
        if risk_assessment.requires_confirmation:
            # 更新thread状态为等待确认
            await supabase_client.update_thread_status(
                thread_id, 
                ThreadStatus.WAITING_CONFIRMATION
            )
            
            # 发送中断信号给前端
            yield f"event: {SSEEventType.INTERRUPT.value}\n"
            yield f"data: {StreamResponseType.REQUIRE_USER_CONFIRM.value}\n\n"
            
            logger.info(f"Thread {thread_id} 进入等待用户确认状态")
        
    except Exception as e:
        logger.error(f"处理消息时出错: {str(e)}")
        yield f"event: {SSEEventType.ERROR.value}\n"
        yield f"data: 处理消息时发生错误: {str(e)}\n\n"


@app.post("/api/v1/stream_chat", response_model=StreamChatResponse)
async def stream_chat_endpoint(request: StreamChatRequest):
    """
    处理流式聊天请求的主入口点
    """
    try:
        # 验证thread_id
        if not request.thread_id:
            raise HTTPException(status_code=400, detail="thread_id是必需的")
        
        return StreamingResponse(
            stream_chat_handler(request.message, request.thread_id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # 禁用Nginx缓冲
            }
        )
        
    except Exception as e:
        logger.error(f"Endpoint错误: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/threads/{thread_id}/resume")
async def resume_thread(thread_id: str):
    """
    Resume执行中断的线程（用户确认后调用）
    """
    try:
        # 检查当前状态
        thread_state = await supabase_client.get_thread(thread_id)
        if not thread_state:
            raise HTTPException(status_code=404, detail="Thread未找到")
        
        if thread_state.status != ThreadStatus.WAITING_CONFIRMATION:
            raise HTTPException(status_code=400, detail="Thread不在等待确认状态")
        
        # 更新状态为活跃，继续执行
        await supabase_client.update_thread_status(thread_id, ThreadStatus.ACTIVE)
        
        logger.info(f"Thread {thread_id} 已被用户恢复")
        
        return {"message": "Thread已恢复", "thread_id": thread_id}
        
    except Exception as e:
        logger.error(f"恢复thread时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/threads/{thread_id}")
async def get_thread_status(thread_id: str):
    """
    获取thread的当前状态
    """
    try:
        thread_state = await supabase_client.get_thread(thread_id)
        if not thread_state:
            raise HTTPException(status_code=404, detail="Thread未找到")
        
        return thread_state
        
    except Exception as e:
        logger.error(f"获取thread状态时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """
    健康检查端点
    """
    return {
        "status": "healthy", 
        "timestamp": datetime.utcnow().isoformat(),
        "supabase_connected": await supabase_client.check_connection()
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
