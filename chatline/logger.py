import os
import logging

def setup_logger(name: str) -> logging.Logger:
    """
    Configure a logger that writes to the project's top-level logs directory.
    """
    # Determine the project root (one level up from the 'chatline' package)
    project_root = os.path.dirname(os.path.dirname(__file__))
    logs_dir = os.path.join(project_root, 'logs')
    os.makedirs(logs_dir, exist_ok=True)

    # Configure logging: all messages at DEBUG level and above go to a file.
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        filename=os.path.join(logs_dir, 'chat_debug.log')
    )
    
    return logging.getLogger(name)

def get_logger(name: str, logging_enabled: bool = False) -> logging.Logger:
    """
    Returns a logger instance.
    
    - If logging_enabled is True, the logger is configured to write logs to file.
    - Otherwise, the logger is given a NullHandler so that logging calls are ignored.
    """
    if logging_enabled:
        return setup_logger(name)
    else:
        logger = logging.getLogger(name)
        if not logger.handlers:
            logger.addHandler(logging.NullHandler())
        return logger
