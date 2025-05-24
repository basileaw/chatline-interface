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
                 history_file: Optional[str] = None,
                 aws_config: Optional[Dict[str, Any]] = None,
                 provider: str = DEFAULT_PROVIDER,
                 provider_config: Optional[Dict[str, Any]] = None,
                 conclusion: Optional[str] = None):
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
            history_file: Path to conversation history JSON file. If None, defaults to
                          "conversation_history.json" in the same directory as log_file.
            aws_config: (Legacy) AWS configuration dictionary with keys like:
                        - region: AWS region for Bedrock
                        - profile_name: AWS profile to use
                        - model_id: Bedrock model ID
                        - timeout: Request timeout in seconds
            provider: Provider name (e.g., 'bedrock', 'openrouter')
            provider_config: Provider-specific configuration
            conclusion: Optional conclusion string that terminates input prompts
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
                              history_file,
                              provider,
                              provider_config,
                              conclusion)

    def _init_components(self,
                         endpoint: Optional[str],
                         use_same_origin: bool,
                         origin_path: str,
                         origin_port: Optional[int],
                         logging_enabled: bool,
                         log_file: Optional[str],
                         history_file: Optional[str],
                         provider: str = DEFAULT_PROVIDER,
                         provider_config: Optional[Dict[str, Any]] = None,
                         conclusion: Optional[str] = None) -> None:
        """
        Internal helper to initialize logger, display, stream, and conversation components.
        """
        try:
            self.logger = Logger(__name__, logging_enabled, log_file, history_file)
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
                logger=self.logger,
                conclusion_string=conclusion
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
        
        In remote mode with no messages (None), uses a special initialization message
        that signals to the server to use its default messages.
        
        In embedded mode with no messages (None), uses DEFAULT_MESSAGES.
        
        An explicitly empty array ([]) will bypass defaults in any mode.
        """
        # Only apply defaults when messages is explicitly None
        if messages is None:
            if hasattr(self, 'is_remote_mode') and self.is_remote_mode:
                # For remote mode, use a special initialization message
                messages = [{"role": "user", "content": "___INIT___"}]
            else:
                # For embedded mode, use default messages
                messages = DEFAULT_MESSAGES.copy()

        # Only validate message structure if we have non-empty messages
        if messages:
            # Ensure final message is from user
            if messages[-1]["role"] != "user":
                raise ValueError("Messages must a user a user message.")

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

        # Start the conversation
        self.conv.actions.start_conversation(messages)
