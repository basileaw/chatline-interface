# interface.py

from typing import Optional, Dict
from .display import Display
from .stream import Stream
from .logger import Logger
from .conversation import Conversation

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

    def preface(self, text: str, color: Optional[str] = None, display_type: str = "panel", 
            title: Optional[str] = None, border_color: Optional[str] = None) -> None:
        """Display preface text before starting the conversation.
        
        Args:
            text: The text to display in the preface
            color: Optional color for the text (default: white)
            display_type: The type of display (default: "panel")
            title: Optional title for the panel
            border_color: Optional color for the panel border (default: white)
        """
        self.conv.preface.add_content(text, color, display_type, title, border_color)

    def start(self, messages: Dict[str, str]) -> None:
        """Start the conversation with the provided messages."""
        self.conv.actions.start_conversation(messages)