#!/usr/bin/env python3
"""
简化实现 - 基于新API协议的重点修复
专注于解决Thread ID连续性问题
"""

from fastapi import FastAPI, Request
import uuid
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mock conversation manager (simplified for core testing)
class SimplifiedConversationManager:
    def __init__(self):
        self.threads = {}  # thread_id -> state dict
        
    async def process_message(self, message: str, thread_id: str):
        """简化流程：确保thread_id一致性"""
        logger.info(f"[SIMPLIFIED] 开始处理: '{message}' | thread_id: {thread_id}")
        
        # 1. 加载或创建thread状态
        if thread_id not in self.threads:
            logger.info(f"[SIMPLIFIED] 创建新线程: {thread_id}")
            self.threads[thread_id] = {
                "address_slot": None,
                "messages": []
            }
        else:
            logger.info(f"[SIMPLIFIED] 重用现有线程: {thread_id}")
            
        state = self.threads[thread_id]
        state["messages"].append({"role": "user", "content": message, "time": "now"})
        
        # 2. 应用新协议的地址逻辑
        if not state["address_slot"]:
            # 需要询问地址
            response = "能告诉我你在哪个区域吗？我帮你查查附近有什么安静的地方~"
            logger.info(f"[SIMPLIFIED] 地址未设置，询问用户 | 保持thread_id: {thread_id}")
        else:
            # 已有地址，提供推荐  
            response = f"你之前在{state['address_slot']['location']}！为推荐几个好去处..."
            logger.info(f"[SIMPLIFIED] 地址已设置: {state['address_slot']['location']} | 保持thread_id: {thread_id}")
            
        # 3. 检查地址更新
        if self._is_location_message(message):
            state["address_slot"] = {
                "location": message,
                "source": "user",
                "confidence": 1.0
            }
            response = f"好的，现在我知道你在{message}了！你想找什么样的地方呢？"
            logger.info(f"[SIMPLIFIED] 更新地址: {message} | 保持thread_id: {thread_id}")
        
        state["messages"].append({"role": "assistant", "content": response, "time": "now"})
        
        # 重要：始终返回相同thread_id
        return {"response": response}, thread_id
        
    def _is_location_message(self, text: str):
        """简单地址检测（仅正例）"""
        locations = ["海淀区", "朝阳区", "静安区", "宝山区", "上海", "北京"]
        return any(loc in text for loc in locations)

# 创建应用
app = FastAPI()
conversation_manager = SimplifiedConversationManager()

@app.post("/api/chat")
async def chat_endpoint(request: Request):
    try:
        # 1. 解析输入
        data = await request.json()
        user_message = data.get("message", "")
        
        # 2. 获取thread_id（新协议逻辑）
        thread_id = None
        if "thread_id" in data:
            thread_id = data["thread_id"]  # 优先使用body中的thread_id
        elif hasattr(request, 'query_params'):
            thread_id = request.query_params.get("thread_id")
            
        # 3. 若没有thread_id，才创建新的
        if not thread_id:
            thread_id = str(uuid.uuid4())
            logger.info(f"[Simplified-Main] 无thread_id，创建新ID: {thread_id}")
        else:
            logger.info(f"[Simplified-Main] 重用thread_id: {thread_id}")
            
        # 4. 处理消息
        process_result, final_thread_id = await conversation_manager.process_message(
            message=user_message,
            thread_id=thread_id
        )
        
        # 5. 确保返回一致性（重要！）
        if thread_id != final_thread_id:
            logger.warning(f"[Simplified-Main] Thread ID不一致: {thread_id} != {final_thread_id}")
            final_thread_id = thread_id  # 强制保持一致
            
        logger.info(f"[Simplified-Main] 成功处理 | thread_id: {final_thread_id}")
        
        return {
            "response": process_result["response"],
            "thread_id": final_thread_id,
            "state_info": {
                "has_location": thread_id in conversation_manager.threads and conversation_manager.threads[thread_id]["address_slot"] is not None
            }
        }
        
    except Exception as e:
        logger.error(f"[Simplified-Main] Error: {e}")
        return {
            "response": f"抱歉，我遇到了问题: {str(e)}",
            "thread_id": str(uuid.uuid4())  # 错误时也创建新thread
        }

if __name__ == "__main__":
    import uvicorn
    logger.info("启动简化API服务器...")
    uvicorn.run(app, host="127.0.0.1", port=8001)
    

else:
    # For debugging
    pass