#!/usr/bin/env python3
import sys
import os
import asyncio
import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add backend to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

async def main():
    try:
        # Import after logging setup
        from services.agent.langgraph_agent import LangGraphAgent
        from data_types import ThreadState, ThreadStatus
        from datetime import datetime

        # Test the process_message directly
        agent = LangGraphAgent(supabase_client=None)

        message = "我在上海市宝山区锦秋路附近，想找咖啡店"
        thread_state = ThreadState(
            thread_id="test-thread",
            status=ThreadStatus.ACTIVE,
            messages=[
                {
                    "role": "user",
                    "content": message,
                    "timestamp": datetime.now().isoformat()
                }
            ],
            metadata={},
            created_at=datetime.now().isoformat()
        )

        logger.info(f"Input message: {message}")

        process_result = await agent.process_message(
            message=message,
            thread_state=thread_state
        )

        print(f"Process result keys: {list(process_result.keys())}")
        print(f"Result type: {process_result.get('type')}")
        
        detailed_scenario = process_result.get("detailed_scenario")
        print(f"Detailed scenario type: {type(detailed_scenario)}")
        print(f"Detailed scenario: {detailed_scenario}")
                
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())