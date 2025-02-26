# interface.py

from typing import Dict, Optional, List

from .logger import Logger
from .default_messages import DEFAULT_MESSAGES
from .display import Display
from .stream import Stream
from .conversation import Conversation
from .generator import generate_stream

class Interface:
    """
    Main entry point that assembles our Display, Stream, and Conversation.
    """

    def __init__(self, endpoint: Optional[str] = None, 
                 logging_enabled: bool = False,
                 log_file: Optional[str] = None):
        """
        Initialize components with an optional endpoint and logging.
        
        Args:
            endpoint: URL endpoint for remote mode. If None, embedded mode is used.
            logging_enabled: Enable detailed logging.
            log_file: Path to log file. Use "-" for stdout.
        """
        self._init_components(endpoint, logging_enabled, log_file)
    
    def _init_components(self, endpoint: Optional[str], 
                         logging_enabled: bool,
                         log_file: Optional[str]) -> None:
        try:
            # Our custom logger, which can also handle JSON logs
            self.logger = Logger(__name__, logging_enabled, log_file)

            self.display = Display()
            self.stream = Stream.create(endpoint, logger=self.logger, generator_func=generate_stream)

            # Pass the entire logger down so conversation/history can use logger.write_json
            self.conv = Conversation(
                display=self.display,
                stream=self.stream,
                logger=self.logger
            )

            self.display.terminal.reset()
            
            # Track if we're in remote mode
            self.is_remote_mode = endpoint is not None
            if self.is_remote_mode:
                self.logger.debug(f"Initialized in remote mode with endpoint: {endpoint}")
            else:
                self.logger.debug("Initialized in embedded mode")
                
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"Init error: {e}")
            raise

    def preface(self, text: str, title: Optional[str] = None,
                border_color: Optional[str] = None, display_type: str = "panel") -> None:
        """Display preface text before starting the conversation."""
        self.conv.preface.add_content(
            text=text,
            title=title,
            border_color=border_color,
            display_type=display_type
        )

    def start(self, messages: Optional[List[Dict[str, str]]] = None) -> None:
        """
        Start the conversation with optional messages.
        
        If no messages are provided, default messages will be used in both
        embedded and remote modes.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content' keys.
                     If None, default messages will be used.
        """
        if messages is None:
            self.logger.debug("No messages provided. Using default messages.")
            messages = DEFAULT_MESSAGES.copy()
        
        # Extract system and user messages for ConversationActions
        system_content = ""
        user_content = ""
        
        for msg in messages:
            if msg["role"] == "system":
                system_content = msg["content"]
            elif msg["role"] == "user" and not user_content:  # Take first user message
                user_content = msg["content"]
        
        # Start conversation with extracted messages
        self.conv.actions.start_conversation({
            "system": system_content,
            "user": user_content
        })