# __init__.py

import os, logging
from typing import Dict, Optional
from functools import partial
from .display import Display
from .stream import Stream
from .conversation import Conversation

class Logger:
    def __init__(self, name: str, logging_enabled: bool = False):
        self._logger = logging.getLogger(name)
        if logging_enabled:
            project_root = os.path.dirname(os.path.dirname(__file__))
            os.makedirs(os.path.join(project_root, 'logs'), exist_ok=True)
            logging.basicConfig(
                level=logging.DEBUG,
                format='%(asctime)s - %(levelname)s - %(message)s',
                filename=os.path.join(project_root, 'logs', 'chat_debug.log')
            )
        else:
            self._logger.addHandler(logging.NullHandler())
            
        # Dynamically create logging methods
        for level in ['debug', 'info', 'warning', 'error']:
            setattr(self, level, partial(self._log, level))
            
    def _log(self, level: str, msg: str, exc_info: Optional[bool] = None) -> None:
        getattr(self._logger, level)(msg, exc_info=exc_info)

class Interface:
    """Manages display, conversation, streaming, and logging."""
    
    def __init__(self, endpoint: Optional[str] = None, logging_enabled: bool = False):
        """Initialize components with an optional endpoint and logging."""
        self._init_components(endpoint, logging_enabled)

    def _init_components(self, endpoint: Optional[str], logging_enabled: bool) -> None:
        """Set up Logger, Display, Stream, and Conversation."""
        try:
            self.logger = Logger(__name__, logging_enabled)  # Init logger
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