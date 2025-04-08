# interface.py

from typing import Dict, Optional, List, Any
import socket

from .logger import Logger
from .default_messages import DEFAULT_MESSAGES
from .display import Display
from .stream import Stream
from .conversation import Conversation
from .generator import generate_stream, DEFAULT_PROVIDER


class Interface:
    """
    Main entry point that assembles our Display, Stream, and Conversation.
    Allows starting a conversation with an arbitrary list of messages
    (including multiple user/assistant pairs) as long as the conversation
    ends on a user message.
    """

    def __init__(self,
                 endpoint: Optional[str] = None,
                 use_same_origin: bool = False,
                 origin_path: str = "/chat",
                 origin_port: Optional[int] = None,
                 logging_enabled: bool = False,
                 log_file: Optional[str] = None,
                 aws_config: Optional[Dict[str, Any]] = None,
                 provider: str = DEFAULT_PROVIDER,
                 provider_config: Optional[Dict[str, Any]] = None):
        """
        Initialize components with an optional endpoint and logging.
        
        Args:
            endpoint: URL endpoint for remote mode. If None and use_same_origin is False, 
                      embedded mode is used.
            use_same_origin: If True, attempts to determine server origin automatically.
            origin_path: Path component to use when constructing same-origin URL.
            origin_port: Port to use when constructing same-origin URL. 
                         If None, uses default ports.
            logging_enabled: Enable detailed logging.
            log_file: Path to log file. Use "-" for stdout.
            aws_config: (Legacy) AWS configuration dictionary with keys like:
                        - region: AWS region for Bedrock
                        - profile_name: AWS profile to use
                        - model_id: Bedrock model ID
                        - timeout: Request timeout in seconds
            provider: Provider name (e.g., 'bedrock', 'openrouter')
            provider_config: Provider-specific configuration
        """
        # For backward compatibility: if aws_config is provided but provider_config is not,
        # and the provider is 'bedrock', use aws_config as the provider_config
        if provider == "bedrock" and aws_config and not provider_config:
            provider_config = aws_config

        self._init_components(endpoint,
                              use_same_origin,
                              origin_path,
                              origin_port,
                              logging_enabled,
                              log_file,
                              provider,
                              provider_config)

    def _init_components(self,
                         endpoint: Optional[str],
                         use_same_origin: bool,
                         origin_path: str,
                         origin_port: Optional[int],
                         logging_enabled: bool,
                         log_file: Optional[str],
                         provider: str = DEFAULT_PROVIDER,
                         provider_config: Optional[Dict[str, Any]] = None) -> None:
        """
        Internal helper to initialize logger, display, stream, and conversation components.
        """
        try:
            self.logger = Logger(__name__, logging_enabled, log_file)
            self.display = Display()

            # Handle same-origin case
            if use_same_origin and not endpoint:
                try:
                    hostname = socket.gethostname()
                    try:
                        ip_address = socket.gethostbyname(hostname)
                    except:
                        ip_address = "localhost"
                    port = origin_port or 8000
                    endpoint = f"http://{ip_address}:{port}{origin_path}"
                    self.logger.debug(f"Auto-detected same-origin endpoint: {endpoint}")
                except Exception as e:
                    self.logger.error(f"Failed to determine origin: {e}")
                    # Continue with embedded mode if we can't determine the endpoint

            # Log (safe) provider config
            if provider_config and self.logger:
                safe_config = {
                    k: v for k, v in provider_config.items()
                    if k not in (
                        'api_key', 'aws_access_key_id',
                        'aws_secret_access_key', 'aws_session_token'
                    )
                }
                if safe_config:
                    self.logger.debug(f"Using provider '{provider}' with config: {safe_config}")

            # Create appropriate Stream object
            self.stream = Stream.create(
                endpoint,
                logger=self.logger,
                generator_func=generate_stream,
                provider=provider,
                provider_config=provider_config
            )

            # Create our main conversation object
            self.conv = Conversation(
                display=self.display,
                stream=self.stream,
                logger=self.logger
            )

            self.display.terminal.reset()

            # Track mode
            self.is_remote_mode = endpoint is not None
            if self.is_remote_mode:
                self.logger.debug(f"Initialized in remote mode with endpoint: {endpoint}")
            else:
                self.logger.debug(f"Initialized in embedded mode with provider: {provider}")

        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"Init error: {e}")
            raise

    def preface(self,
                text: str,
                title: Optional[str] = None,
                border_color: Optional[str] = None,
                display_type: str = "panel") -> None:
        """
        Display a "preface" panel (optionally titled/bordered) before
        starting the conversation.
        """
        self.conv.preface.add_content(
            text=text,
            title=title,
            border_color=border_color,
            display_type=display_type
        )

    def start(self, messages: Optional[List[Dict[str, str]]] = None) -> None:
        """
        Start the conversation with optional messages.
        
        The messages list can contain:
        - An optional system message at the start
        - Zero or more user/assistant pairs
        - Must end with a user message (so the next reply can be generated)
        
        Example of a valid messages list:
        
        [
          {"role": "system", "content": "You're a friendly AI."},
          {"role": "user", "content": "Hello!"},
          {"role": "assistant", "content": "Hi there!"},
          {"role": "user", "content": "What's up?"}
        ]
        
        Args:
            messages: List of message dictionaries with roles "system", "user", or "assistant".
                      If None, default_messages will be used.
        
        Raises:
            ValueError: If invalid roles or ordering, or if not ending in user.
        """
        if messages is None:
            self.logger.debug("No messages provided. Using default messages.")
            messages = DEFAULT_MESSAGES.copy()

        if not messages:
            raise ValueError("Messages list cannot be empty")

        # Ensure final message is from user
        if messages[-1]["role"] != "user":
            raise ValueError("Messages must end with a user message.")

        # Optional: check if the first message is system
        has_system = (messages[0]["role"] == "system")

        # We'll start validating from the *first non-system* message
        start_idx = 1 if has_system else 0

        # Enforce strict alternating from that point on
        # e.g. user -> assistant -> user -> assistant -> ...
        for i in range(start_idx, len(messages)):
            expected = "user" if i % 2 == start_idx % 2 else "assistant"
            actual = messages[i]["role"]
            if actual != expected:
                raise ValueError(
                    f"Invalid role order at index {i}. "
                    f"Expected '{expected}', got '{actual}'."
                )

        # If we pass all checks, proceed:
        self.conv.actions.start_conversation(messages)
