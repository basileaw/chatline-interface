# interface.py

from typing import Dict, Optional, List, Any
import socket

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
                 use_same_origin: bool = False,
                 origin_path: str = "/chat", 
                 origin_port: Optional[int] = None,
                 logging_enabled: bool = False,
                 log_file: Optional[str] = None,
                 aws_config: Optional[Dict[str, Any]] = None):
        """
        Initialize components with an optional endpoint and logging.
        
        Args:
            endpoint: URL endpoint for remote mode. If None and use_same_origin is False, embedded mode is used.
            use_same_origin: If True, attempts to determine server origin automatically.
            origin_path: Path component to use when constructing same-origin URL.
            origin_port: Port to use when constructing same-origin URL. If None, uses default ports.
            logging_enabled: Enable detailed logging.
            log_file: Path to log file. Use "-" for stdout.
            aws_config: Optional AWS configuration dictionary with keys like:
                        - region: AWS region for Bedrock
                        - profile_name: AWS profile to use
                        - model_id: Bedrock model ID
                        - timeout: Request timeout in seconds
        """
        self._init_components(endpoint, use_same_origin, origin_path, 
                              origin_port, logging_enabled, log_file, aws_config)
    
    def _init_components(self, endpoint: Optional[str], 
                         use_same_origin: bool,
                         origin_path: str,
                         origin_port: Optional[int],
                         logging_enabled: bool,
                         log_file: Optional[str],
                         aws_config: Optional[Dict[str, Any]] = None) -> None:
        try:
            # Our custom logger, which can also handle JSON logs
            self.logger = Logger(__name__, logging_enabled, log_file)

            self.display = Display()
            
            # Handle same-origin case
            if use_same_origin and not endpoint:
                try:
                    # Try to determine the origin automatically
                    hostname = socket.gethostname()
                    # Get container IP if possible
                    try:
                        ip_address = socket.gethostbyname(hostname)
                    except:
                        ip_address = "localhost"  # Fallback
                    
                    port = origin_port or 8000  # Default to 8000 if not specified
                    endpoint = f"http://{ip_address}:{port}{origin_path}"
                    self.logger.debug(f"Auto-detected same-origin endpoint: {endpoint}")
                except Exception as e:
                    self.logger.error(f"Failed to determine origin: {e}")
                    # Continue with embedded mode if we can't determine the endpoint
            
            # Log AWS configuration if provided
            if aws_config and self.logger:
                # Don't log sensitive credential values
                safe_config = {k: v for k, v in aws_config.items() 
                              if k not in ('aws_access_key_id', 'aws_secret_access_key', 'aws_session_token')}
                if safe_config:
                    self.logger.debug(f"Using AWS config: {safe_config}")
            
            # Pass AWS config to Stream.create
            self.stream = Stream.create(
                endpoint, 
                logger=self.logger, 
                generator_func=generate_stream,
                aws_config=aws_config
            )

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
        elif len(messages) == 2:
            if messages[0]["role"] != "system" or messages[1]["role"] != "user":
                raise ValueError("Two messages must be system followed by user")
        else:
            raise ValueError("Messages must contain either 1 user message or 1 system + 1 user message")
        
        # Start conversation with validated messages - pass the list directly
        self.conv.actions.start_conversation(messages)