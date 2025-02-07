# logger.py

import os
import logging

def setup_logger(name: str) -> logging.Logger:
    # Ensure the logs directory exists
    logs_dir = os.path.join(os.path.dirname(__file__), 'logs')
    os.makedirs(logs_dir, exist_ok=True)

    # Configure logging exactly as before
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        filename=os.path.join(logs_dir, 'chat_debug.log')
    )
    
    return logging.getLogger(name)
