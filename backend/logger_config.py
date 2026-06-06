#!/usr/bin/env python3
import logging

# Configure root logger to capture all errors
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('d:/SOLOVIBE/backend/server_trace.log'),
        logging.StreamHandler()]
)

logger = logging.getLogger(__name__)
logger.info("Logging configured")
