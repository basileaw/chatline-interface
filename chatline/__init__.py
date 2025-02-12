# __init__.py

import sys, logging
from typing import Dict, Optional
from functools import partial
from .display import Display
from .stream import Stream
from .conversation import Conversation

class Logger:
    def __init__(self, name: str, logging_enabled: bool = False, log_file: Optional[str] = None):
        self._logger = logging.getLogger(name)
        self._logger.propagate = False
        
        if logging_enabled:
            # Determine output destination
            if log_file == '-':
                handler = logging.StreamHandler(sys.stdout)
            elif log_file:
                handler = logging.FileHandler(log_file)
            else:
                handler = logging.StreamHandler(sys.stderr)
            
            handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            
            self._logger.addHandler(handler)
            self._logger.setLevel(logging.DEBUG)
        else:
            self._logger.addHandler(logging.NullHandler())

        # Dynamically create logging methods
        for level in ['debug', 'info', 'warning', 'error']:
            setattr(self, level, partial(self._log, level))

    def _log(self, level: str, msg: str, exc_info: Optional[bool] = None) -> None:
        getattr(self._logger, level)(msg, exc_info=exc_info)

class Interface:
    def __init__(self, endpoint: Optional[str] = None, 
                 logging_enabled: bool = False,
                 log_file: Optional[str] = None):
        """Initialize components with an optional endpoint and logging."""
        self._init_components(endpoint, logging_enabled, log_file)
    
    def _init_components(self, endpoint: Optional[str], 
                        logging_enabled: bool,
                        log_file: Optional[str]) -> None:
        try:
            self.logger = Logger(__name__, logging_enabled, log_file)
            self.display = Display()  # Init display
            self.stream = Stream.create(endpoint, logger=self.logger)
            self.conv = Conversation(display=self.display, stream=self.stream, logger=self.logger)
            self.display.terminal.reset()  # Reset terminal
        except Exception as e:
            self.logger.error(f"Init error: {e}")
            raise

    def preface(self, text: str, title: Optional[str] = None, border_color: Optional[str] = None, display_type: str = "panel") -> None:
        """Display preface text before starting the conversation.
        
        Args:
            text: The main text content to display
            title: Optional title to show in the panel
            border_color: Optional color for the panel border
            display_type: Type of display ("panel" by default)
        """
        self.conv.preface.add_content(
            text=text,
            title=title,
            border_color=border_color,
            display_type=display_type
        )

    def start(self, messages: Dict[str, str]) -> None:
        """Start the conversation with the provided messages."""
        self.conv.actions.start_conversation(messages)

__all__ = ['Interface']