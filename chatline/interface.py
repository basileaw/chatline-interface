# interface.py

from typing import Optional, Dict
from .display import Display
from .stream import Stream
from .logger import get_logger
from .conversation import Conversation

class Interface:
    """Chat coordinator: manages display, conversation, stream, and logging."""
    def __init__(self, endpoint: Optional[str] = None, logging_enabled: bool = False):
        """Initialize interface with an optional endpoint and logging setting."""
        self.logger = get_logger(__name__, logging_enabled)
        self._init_components(endpoint)

    def _init_components(self, endpoint: Optional[str]) -> None:
        """Set up display, stream, and conversation components."""
        try:
            self.display = Display()  
            self.stream = Stream.create(endpoint, logger=self.logger)
            self.conv = Conversation(
                display=self.display, 
                stream=self.stream,
                logger=self.logger
            )  
            self.display.terminal.reset()  # Reset terminal
        except Exception as e:
            self.logger.error(f"Init error: {e}")
            raise

    def preface(self, text: str, color: Optional[str] = None, display_type: str = "panel") -> None:
        """Display preface text before starting conversation."""
        self.conv.actions.add_preface(text, color, display_type)

    def start(self, messages: Dict[str, str]) -> None:
        """Begin conversation with provided messages."""
        self.conv.actions.start_conversation(messages)