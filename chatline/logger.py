import os
import logging

def setup_logger(name: str) -> logging.Logger:
    # Calculate the project root directory (one level up from chatline/)
    project_root = os.path.dirname(os.path.dirname(__file__))
    logs_dir = os.path.join(project_root, 'logs')
    os.makedirs(logs_dir, exist_ok=True)

    # Configure logging as before, but using the new logs_dir path
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        filename=os.path.join(logs_dir, 'chat_debug.log')
    )
    
    return logging.getLogger(name)
