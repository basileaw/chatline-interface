# logger.py

import os
import logging
from typing import Optional

class Logger:
    """Logger class that handles all logging operations for the chat application.
    Follows similar pattern to other components like Display."""
    
    def __init__(self, name: str, logging_enabled: bool = False):
        """Initialize the logger.
        Args:
            name: Name for the logger instance
            logging_enabled: Whether to enable file logging
        """
        self._logger = logging.getLogger(name)
        if logging_enabled:
            self._setup_file_logging()
        else:
            self._logger.addHandler(logging.NullHandler())
            
    def _setup_file_logging(self) -> None:
        """Configure file-based logging."""
        project_root = os.path.dirname(os.path.dirname(__file__))
        logs_dir = os.path.join(project_root, 'logs')
        os.makedirs(logs_dir, exist_ok=True)
        
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s',
            filename=os.path.join(logs_dir, 'chat_debug.log')
        )

    # Delegate logging methods to internal logger with exc_info support
    def debug(self, msg: str, exc_info: Optional[bool] = None) -> None:
        self._logger.debug(msg, exc_info=exc_info)
        
    def info(self, msg: str, exc_info: Optional[bool] = None) -> None:
        self._logger.info(msg, exc_info=exc_info)
        
    def warning(self, msg: str, exc_info: Optional[bool] = None) -> None:
        self._logger.warning(msg, exc_info=exc_info)
        
    def error(self, msg: str, exc_info: Optional[bool] = None) -> None:
        self._logger.error(msg, exc_info=exc_info)