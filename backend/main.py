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
    基于PRD的慢生活轨道流式聊天处理器
    情感感知 → 独享任务生成 → HITL中断点
    """
    try:
        logger.info(f"开始处理thread_id: {thread_id}, message: {message}")
        
        # 1. 从Supabase恢复或创建thread状态
        thread_state = await supabase_client.get_or_create_thread(thread_id)
        
        # 2. 通过LangGraph Agent处理消息
        agent_response = await langgraph_agent.process_message(message, thread_state)
        
        # 3. 处理不同类型的响应
        if agent_response["type"] == "clarification":
            # 需要澄清的情况 - 发送同理心回应和选项
            yield f"data: {StreamResponseType.EMPATHY.value} {agent_response['empathy_response']}\n\n"
            await asyncio.sleep(0.5)
            
            # 发送选项作为计划格式（便于前端解析）
            options_plan = {
                "type": "clarification_options",
                "options": agent_response["options"],
                "instruction": "请选择最符合您当前心境的选项"
            }
            yield f"data: {StreamResponseType.PLANS.value} {json.dumps(options_plan, ensure_ascii=False)}\n\n"
            
        elif agent_response["type"] == "complete_response":
            # 完整响应 - 慢生活轨道流程
            
            # 发送同理心回应
            yield f"data: {StreamResponseType.EMPATHY.value} {agent_response['empathy_response']}\n\n"
            await asyncio.sleep(0.8)
            
            # 发送独享任务（计划）
            quest_data = {
                "type": "solo_quest",
                "id": f"quest-{thread_id}-{int(datetime.utcnow().timestamp())}",
                **agent_response["quest"]
            }
            yield f"data: {StreamResponseType.PLANS.value} {json.dumps(quest_data, ensure_ascii=False)}\n\n"
            
            await asyncio.sleep(0.5)
            
            # 发送详细方案信息（包含商家、路线、时间等完整数据）
            if "detailed_scenario" in agent_response:
                detailed_data = {
                    "type": "detailed_scenario",
                    "id": f"scenario-{thread_id}-{int(datetime.utcnow().timestamp())}",
                    **agent_response["detailed_scenario"]
                }
                yield f"data: {StreamResponseType.PLANS.value} {json.dumps(detailed_data, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0.5)
            
            await asyncio.sleep(1)
            
            # 发送匿名共鸣信息
            copresence_info = {
                "type": "copresence_data",
                **agent_response["copresence"]
            }
            yield f"data: {StreamResponseType.EMPATHY.value} ✨ {copresence_info['message']}\n\n"
            
            # 4. 风控检查 - 判断是否需要HITL确认
            if agent_response["requires_confirmation"]:
                risk_assessment = await verify_action_risk(quest_data, thread_state)
                
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
            
            # 更新用户历史偏好
            await supabase_client.update_thread_metadata(
                thread_id,
                {
                    "last_successful_vibe": agent_response["quest"]["chips"][0] if agent_response["quest"]["chips"] else "安静角落",
                    "last_quest_completed": agent_response["quest"]["title"],
                    "agent_mode_used": agent_response["quest"]["difficulty"]
                }
            )
        
    except Exception as e:
        logger.error(f"处理消息时出错: {str(e)}")
        error_message = "抱歉，我的大脑稍微有点断网了 🧠💦。不过别担心，给你推荐去附近的河边散散步、喝一杯醇厚的手冲咖啡吧！"
        yield f"event: {SSEEventType.ERROR.value}\n"
        yield f"data: {StreamResponseType.EMPATHY.value} {error_message}\n\n"


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
