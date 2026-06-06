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
        from db.supabase_client import supabase_client

        # Test the process_message directly
        agent = LangGraphAgent()

        message = "上海市宝山区锦秋路附近"
        thread_state = {
            'has_location': False,
            'needs_user_input': True
        }

        logger.info(f"Input message: {message}")

        process_result = await agent.process_message(
            message=message,
            thread_state=thread_state
        )

        logger.info(f"Result: {json.dumps(process_result, ensure_ascii=False, indent=2)}")

        detailed_scenario = process_result.get("detailed_scenario")
        logger.info(f"Detailed scenario: {detailed_scenario}")
        if detailed_scenario:
            logger.info(f"Keys/attributes: {dir(detailed_scenario)}")
            if hasattr(detailed_scenario, 'merchant'):
                logger.info(f"Merchant: {detailed_scenario.merchant}")

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())
