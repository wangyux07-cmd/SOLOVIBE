import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

from types import ThreadState, CheckpointData

logger = logging.getLogger(__name__)


class LangGraphAgent:
    """
    LangGraph代理实现（简化模拟版本）
    这个类模拟了LangGraph的核心功能，包括状态管理和工作流执行
    """
    
    def __init__(self):
        self.checkpoint_data = {}
        logger.info("LangGraph Agent 初始化完成")
    
    async def process_message(self, message: str, thread_state: ThreadState) -> Dict[str, Any]:
        """
        处理用户消息并生成响应
        """
        logger.info(f"处理消息: {message}")
        
        # 模拟意图识别
        intent = self._detect_intent(message)
        
        # 生成响应计划
        response_plan = self._generate_response_plan(intent, message)
        
        # 保存检查点
        await self._save_checkpoint(thread_state.thread_id, {
            "intent": intent,
            "response_plan": response_plan,
            "last_message": message
        })
        
        return {
            "intent": intent,
            "plan": response_plan,
            "requires_confirmation": self._requires_confirmation(response_plan)
        }
    
    def _detect_intent(self, message: str) -> str:
        """检测用户意图"""
        message_lower = message.lower()
        
        intent_patterns = {
            "wander_planning": ["想去", "想找", "计划", "安排", "推荐", "地方"],
            "emotional_support": ["心情", "感觉", "难受", "开心", "孤独", "放松"],
            "social_interaction": ["朋友", "聊天", "认识", "交流", "pk", "共鸣"],
            "booking_confirmation": ["确认", "预订", "确定", "yes", "确认"]
        }
        
        for intent, patterns in intent_patterns.items():
            if any(pattern in message_lower for pattern in patterns):
                return intent
        
        return "general_chat"
    
    def _generate_response_plan(self, intent: str, message: str) -> Dict[str, Any]:
        """根据意图生成响应计划"""
        
        base_plan = {
            "empathy_response": "",
            "suggested_actions": [],
            "needs_user_input": False
        }
        
        if intent == "wander_planning":
            base_plan.update({
                "empathy_response": f"我理解您想要独自探索的想法，'{message}' 听起来是个不错的计划。",
                "suggested_actions": [
                    {
                        "type": "wander_plan",
                        "data": {
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
                    }
                ],
                "needs_user_input": True
            })
        
        elif intent == "emotional_support":
            base_plan.update({
                "empathy_response": f"听起来您现在的感受是：{message}。让我为您提供一些舒缓心情的建议。",
                "suggested_actions": [
                    {
                        "type": "emotional_support",
                        "data": {
                            "suggestions": ["深呼吸练习", "听轻音乐", "写日记", "散步"]
                        }
                    }
                ],
                "needs_user_input": False
            })
        
        elif intent == "social_interaction":
            base_plan.update({
                "empathy_response": f"想要认识新朋友或参与互动很棒！'{message}'。",
                "suggested_actions": [
                    {
                        "type": "social_activity",
                        "data": {
                            "activity": "轻量PK挑战",
                            "description": "参与今天的轻量PK挑战，结识志同道合的朋友"
                        }
                    }
                ],
                "needs_user_input": True
            })
        
        else:
            base_plan.update({
                "empathy_response": f"我听到了您的想法：'{message}'。我很乐意帮助您。",
                "suggested_actions": [
                    {
                        "type": "general_assistance",
                        "data": {
                            "offer_help": "我可以为您推荐地方、提供情感支持或安排活动"
                        }
                    }
                ],
                "needs_user_input": False
            })
        
        return base_plan
    
    def _requires_confirmation(self, plan: Dict[str, Any]) -> bool:
        """判断计划是否需要用户确认"""
        # 需要确认的场景：
        # 1. 涉及预订/消费的活动
        # 2. 社交互动
        # 3. 用户明确需要输入的活动
        
        if plan.get("needs_user_input", False):
            return True
        
        for action in plan.get("suggested_actions", []):
            action_type = action.get("type", "")
            if action_type in ["wander_plan", "social_activity", "booking"]:
                # 检查是否涉及费用
                action_data = action.get("data", {})
                if "cost" in action_data or action_type == "booking":
                    return True
        
        return False
    
    async def _save_checkpoint(self, thread_id: str, state: Dict[str, Any]) -> bool:
        """保存检查点状态"""
        checkpoint_id = f"checkpoint-{datetime.utcnow().timestamp()}"
        
        checkpoint_data = CheckpointData(
            thread_id=thread_id,
            checkpoint_id=checkpoint_id,
            state=state,
            timestamp=datetime.utcnow().isoformat()
        )
        
        # 保存到内存
        self.checkpoint_data[checkpoint_id] = checkpoint_data
        
        logger.info(f"检查点 {checkpoint_id} 已保存")
        return True
    
    async def restore_from_checkpoint(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """从检查点恢复状态"""
        if checkpoint_id in self.checkpoint_data:
            checkpoint = self.checkpoint_data[checkpoint_id]
            logger.info(f"从检查点 {checkpoint_id} 恢复状态")
            return checkpoint.state
        
        logger.warning(f"检查点 {checkpoint_id} 未找到")
        return None
    
    async def resume_execution(self, thread_state: ThreadState, user_confirmation: bool = True) -> Dict[str, Any]:
        """恢复中断的执行（用户确认后）"""
        logger.info(f"恢复thread {thread_state.thread_id} 的执行")
        
        # 模拟恢复执行
        if user_confirmation:
            return {
                "status": "resumed",
                "message": "基于您的确认，继续执行计划",
                "next_actions": ["执行预订", "发送详细信息", "更新状态"]
            }
        else:
            return {
                "status": "cancelled",
                "message": "用户取消了操作",
                "next_actions": ["重新规划", "询问新需求"]
            }
    
    def get_agent_status(self) -> Dict[str, Any]:
        """获取代理状态信息"""
        return {
            "total_checkpoints": len(self.checkpoint_data),
            "active_threads": len(set(
                cp.thread_id for cp in self.checkpoint_data.values()
            )),
            "last_activity": datetime.utcnow().isoformat()
        }
