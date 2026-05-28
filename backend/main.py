import asyncio
import json
import logging
from datetime import datetime
from typing import AsyncGenerator, Dict, Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import uvicorn

from data_types import (
    StreamChatRequest, StreamChatResponse, ThreadStatus, 
    SSEEventType, StreamResponseType, ThreadState
)
from db.supabase_client import SupabaseClient
from services.agent.langgraph_agent import LangGraphAgent
from middleware.risk_control import verify_action_risk

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 配置验证函数
def validate_environment_config() -> Dict[str, Any]:
    """验证环境配置是否正确"""
    import os
    
    config_status = {
        "status": "ok",
        "missing_vars": [],
        "warnings": [],
        "supabase": False,
        "web_search": False,
        "booking": False
    }
    
    # 检查基础配置
    supabase_vars = ["SUPABASE_URL", "SUPABASE_KEY"]
    for var in supabase_vars:
        if not os.getenv(var) or os.getenv(var).startswith("your-"):
            config_status["missing_vars"].append(var)
    
    if not config_status["missing_vars"]:
        config_status["supabase"] = True
    
    # 检查Web搜索配置
    tavily_key = os.getenv("TAVILY_API_KEY")
    serper_key = os.getenv("SERPER_API_KEY")
    
    if tavily_key and not tavily_key.startswith("your-"):
        config_status["web_search"] = True
    elif serper_key and not serper_key.startswith("your-"):
        config_status["web_search"] = True
    else:
        config_status["missing_vars"].append("WEB_SEARCH_API")
    
    # 检查高德地图配置（现在是核心必要服务）
    amap_key = os.getenv("AMAP_API_KEY")
    amap_url = os.getenv("AMAP_BASE_URL")
    
    if amap_key and not amap_key.startswith("your-") and amap_url:
        config_status["amap"] = True  # 重命名为amap以反映新架构
        config_status["booking"] = True  # 保持旧引用以保持兼容性
    else:
        config_status["missing_vars"].append("AMAP_API")  # 改为必填项
    
    # 设置整体状态
    if config_status["missing_vars"]:
        config_status["status"] = "error"
    elif config_status["warnings"]:
        config_status["status"] = "warning"
    
    return config_status

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

# API端点定义
@app.get("/")
async def root():
    """主页面"""
    config_status = validate_environment_config()
    return {
        "message": "SoloVibe 后端服务运行中 🚀",
        "docs": "/docs",
        "redoc": "/redoc", 
        "version": "0.1.0",
        "config_status": "ok" if config_status["status"] == "ok" else "needs_setup"
    }

@app.get("/api/v1/health")
async def health_check():
    """健康检查端点"""
    config_status = validate_environment_config()
    
    health_info = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "0.1.0",
        "environment": os.getenv("DEBUG", "production") and "development" or "production"
    }
    
    # 添加配置状态
    health_info["configuration"] = config_status
    
    # 根据配置状态设置HTTP状态
    if config_status["status"] == "error":
        health_info["status"] = "unhealthy"
    elif config_status["status"] == "warning":
        health_info["status"] = "degraded"
    
    return health_info

@app.get("/api/v1/config-status")
async def config_status_endpoint():
    """配置状态详细信息"""
    config_status = validate_environment_config()
    
    # 在开发环境返回详细信息
    if os.getenv("DEBUG", "").lower() == "true":
        return {
            "status": config_status,
            "documentation": "ENVIRONMENT_SETUP.md",
            "setup_helper": "python setup_env.py"
        }
    else:
        # 生产环境仅返回基础状态
        return {
            "status": config_status["status"],
            "needs_setup": bool(config_status["missing_vars"])
        }

# 导入os模块用于环境变量访问
import os

def generate_booking_confirmation_message(booking_info: Dict) -> str:
    """生成预订确认消息"""
    booking_request = booking_info.get("booking_request", {})
    risk_assessment = booking_info.get("risk_assessment", {})
    
    merchant_name = booking_request.get("merchant", "")
    estimated_cost = booking_request.get("estimated_cost", 0)
    risk_level = booking_info.get("risk_level", "medium")
    
    risk_indicators = {
        "low": "预订风险较低",
        "medium": "中等风险，建议确认",
        "high": "高风险预订，请仔细确认",
        "critical": "极高风险，强烈建议确认"
    }
    
    base_message = f"即将为您预订 {merchant_name}，预估费用 ¥{estimated_cost:.2f}"
    
    if risk_level in ["high", "critical"]:
        return f"{base_message}。{risk_indicators.get(risk_level, '')}，这是最后确认机会 ⚠️"
    else:
        return f"{base_message}。{risk_indicators.get(risk_level, '')}，请确认是否继续 🤔"


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
            
            # 检查是否需要实时信息反馈
            if "detailed_scenario" in agent_response and "real_time_status" in str(agent_response.get("detailed_scenario", {})):
                real_time_data = {
                    "type": "real_time_update",
                    "message": "已获取商家最新营业状态",
                    "timestamp": datetime.utcnow().isoformat()
                }
                yield f"data: {StreamResponseType.EMPATHY.value} 🔄 {json.dumps(real_time_data, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0.3)
            
            # 检查预订信息和HITL中断
            if "booking_info" in agent_response and agent_response["booking_info"].get("requires_booking"):
                booking_info = agent_response["booking_info"]
                
                # 发送预订评估结果
                booking_data = {
                    "type": "booking_assessment",
                    "data": booking_info
                }
                yield f"data: {StreamResponseType.PLANS.value} {json.dumps(booking_data, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0.5)
                
                # 如果需要进行用户确认，触发HITL中断
                if booking_info.get("needs_confirmation"):
                    risk_level = booking_info.get("risk_level", "medium")
                    confirmation_message = generate_booking_confirmation_message(booking_info)
                    
                    yield f"data: {StreamResponseType.EMPATHY.value} ⚠️ {confirmation_message}\n\n"
                    await asyncio.sleep(0.8)
                    
                    # 发送确认请求
                    confirmation_data = {
                        "type": "booking_confirmation_required",
                        "risk_level": risk_level,
                        "booking_info": booking_info,
                        "options": [
                            {"action": "confirm_booking", "label": "确认预订", "require_confirmation": True},
                            {"action": "modify_booking", "label": "修改预订"},
                            {"action": "cancel_booking", "label": "取消预订"}
                        ]
                    }
                    
                    await supabase_client.update_thread_status(thread_id, ThreadStatus.WAITING_CONFIRMATION)
                    yield f"event: {SSEEventType.INTERRUPT.value}\n"
                    yield f"data: {StreamResponseType.REQUIRE_USER_CONFIRM.value} {json.dumps(confirmation_data, ensure_ascii=False)}\n\n"
                    
                    logger.info(f"Thread {thread_id} 进入等待预订确认状态")
            
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


@app.get("/api/v2/wander-plans")
async def get_wander_plans():
    """
    获取三种不同方案的UnifiedWanderPlans - 用于新版方案选择页面
    """
    try:
        # 模拟三种不同方案的数据，符合新版PRD要求
        healing_solo_index = {
            "single_seat_friendly": 0.9,
            "environment_quietness": 0.8,
            "solo_package_support": 0.7,
            "no_awkwardness": 0.9,
            "safety_rating": 0.8,
            "accessibility": 0.7
        }
        
        explore_solo_index = {
            "single_seat_friendly": 0.7,
            "environment_quietness": 0.6,
            "solo_package_support": 0.8,
            "no_awkwardness": 0.8,
            "safety_rating": 0.9,
            "accessibility": 0.9
        }
        
        free_solo_index = {
            "single_seat_friendly": 0.8,
            "environment_quietness": 0.9,
            "solo_package_support": 0.9,
            "no_awkwardness": 0.8,
            "safety_rating": 0.7,
            "accessibility": 0.6
        }

        cafe_recommendation = {
            "name": "滨江治愈咖啡馆",
            "address": "滨江区滨江大道123号",
            "distance": "步行5分钟",
            "rating": 4.8,
            "solo_seats": 8,
            "quiet_score": 0.85,
            "phone": "021-12345678"
        }

        plans = [
            {
                "id": "healing-riverside",
                "title": "滨江治愈漫步",
                "emoji": "🌊",
                "subtitle": "听流水声发呆，喂鸽子，吹风15分钟",
                "vibe_tags": ["治愈", "发呆", "低能耗"],
                "estimated_time": "45-60min",
                "solo_index": healing_solo_index,
                "merchant_recommendations": [cafe_recommendation]
            },
            {
                "id": "explore-artstreet",
                "title": "艺术街区漫游",
                "emoji": "🎨",
                "subtitle": "街头涂鸦，独立咖啡，小众设计师店",
                "vibe_tags": ["探索", "创意", "拍照"],
                "estimated_time": "90-120min",
                "solo_index": explore_solo_index,
                "merchant_recommendations": [cafe_recommendation]
            },
            {
                "id": "quiet-park",
                "title": "公园长椅计划",
                "emoji": "🌳",
                "subtitle": "零开销放空，风中读诗，免费治愈",
                "vibe_tags": ["免费", "阅读", "自然"],
                "estimated_time": "30-45min",
                "solo_index": free_solo_index,
                "merchant_recommendations": []
            }
        ]
        
        return {
            "success": True,
            "data": plans
        }
        
    except Exception as e:
        logger.error(f"获取漫游方案时出错: {str(e)}")
        raise HTTPException(status_code=500, detail="获取漫游方案失败")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
