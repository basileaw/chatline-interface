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
        
        Messages must follow one of these formats:
        1. A single user message: [{"role": "user", "content": "..."}]
        2. System message followed by a user message: [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]
        
        If no messages are provided, default messages will be used.
        
        Args:
            messages: List of message dictionaries with proper format.
                     If None, default messages will be used.
                     
        Raises:
            ValueError: If messages don't follow the required format.
        """
        if messages is None:
            self.logger.debug("No messages provided. Using default messages.")
            messages = DEFAULT_MESSAGES.copy()
        
        # Validate message format
        if len(messages) == 1:
            if messages[0]["role"] != "user":
                raise ValueError("Single message must be a user message")
            system_content = ""
            user_content = messages[0]["content"]
        elif len(messages) == 2:
            if messages[0]["role"] != "system" or messages[1]["role"] != "user":
                raise ValueError("Two messages must be system followed by user")
            system_content = messages[0]["content"]
            user_content = messages[1]["content"]
        else:
            raise ValueError("Messages must contain either 1 user message or 1 system + 1 user message")
        
        # Start conversation with validated messages
        self.conv.actions.start_conversation({
            "system": system_content,
            "user": user_content
        })