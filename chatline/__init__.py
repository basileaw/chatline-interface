# __init__.py

import sys, logging
import os, json
from datetime import datetime
from typing import Dict, Optional
from functools import partial

from .display import Display
from .stream import Stream
from .conversation import Conversation

class Logger:
    """
    Custom logger that supports both standard logs and
    optional JSON conversation history logs.
    """

    def __init__(self, name: str, logging_enabled: bool = False, log_file: Optional[str] = None):
        """
        Args:
            name: The logger name.
            logging_enabled: If True, standard logging is turned on.
            log_file: If set, logs go here. If "-", logs go to stdout;
                      if None, logs go to a null handler.
        """
        self._logger = logging.getLogger(name)
        self._logger.propagate = False
        
        # Clear any existing handlers
        self._logger.handlers.clear()
        
        self.logging_enabled = logging_enabled
        self.log_file = log_file
        self.json_history_path = None  # Will hold path for JSON conversation logs

        if logging_enabled:
            # Setup standard log handler
            if log_file == '-':
                handler = logging.StreamHandler(sys.stdout)
            elif log_file:
                handler = logging.FileHandler(log_file, mode='w')
            else:
                handler = logging.StreamHandler(sys.stderr)
            
            handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            
            self._logger.addHandler(handler)
            self._logger.setLevel(logging.DEBUG)

            # Determine if we can also create a JSON-history path
            if log_file and log_file not in ("-", ""):
                log_dir = os.path.dirname(log_file) if os.path.dirname(log_file) else "."
                os.makedirs(log_dir, exist_ok=True)

                session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
                self.json_history_path = os.path.join(
                    log_dir,
                    f"conversation_history_{session_id}.json"
                )
        else:
            # If logging is disabled, use NullHandler
            self._logger.addHandler(logging.NullHandler())

        # Dynamically create logging methods
        for level in ['debug', 'info', 'warning', 'error']:
            setattr(self, level, partial(self._log, level))

    def _log(self, level: str, msg: str, exc_info: Optional[bool] = None) -> None:
        getattr(self._logger, level)(msg, exc_info=exc_info)

    def write_json(self, data):
        """
        If we have a self.json_history_path, write the given
        data object to JSON. Otherwise, do nothing.
        """
        if not self.json_history_path:
            return  # JSON logging not in use
        try:
            with open(self.json_history_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            # Non-critical, just log an error
            self.error(f"Failed to write JSON history: {e}")


class Interface:
    """
    Main entry point that assembles our Display, Stream, and Conversation.
    """

    def __init__(self, endpoint: Optional[str] = None, 
                 logging_enabled: bool = False,
                 log_file: Optional[str] = None):
        """
        Initialize components with an optional endpoint and logging.
        """
        self._init_components(endpoint, logging_enabled, log_file)
    
    def _init_components(self, endpoint: Optional[str], 
                         logging_enabled: bool,
                         log_file: Optional[str]) -> None:
        try:
            # Our custom logger, which can also handle JSON logs
            self.logger = Logger(__name__, logging_enabled, log_file)

            self.display = Display()    # For TUI display
            self.stream = Stream.create(endpoint, logger=self.logger)

            # Pass the entire logger down so conversation/history can use write_json
            self.conv = Conversation(
                display=self.display,
                stream=self.stream,
                logger=self.logger
            )

            self.display.terminal.reset()  # Reset terminal
        except Exception as e:
            self.logger.error(f"Init error: {e}")
            raise

    def preface(self, text: str, title: Optional[str] = None,
                border_color: Optional[str] = None, display_type: str = "panel") -> None:
        """
        Display preface text before starting the conversation.
        """
        self.conv.preface.add_content(
            text=text,
            title=title,
            border_color=border_color,
            display_type=display_type
        )

    def start(self, messages: Dict[str, str]) -> None:
        """
        Start the conversation with the provided messages.
        """
        self.conv.actions.start_conversation(messages)
