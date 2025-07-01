# interface.py

from typing import Dict, Optional, List, Any, Union
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

    def __init__(self, **kwargs):
        """
        Initialize components with an optional endpoint and logging.
        
        Keyword Args:
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
            preface: Optional preface content (string or dict with text, title, border_color, display_type)
            conclusion: Optional conclusion string that terminates input prompts
        """
        # Build interface config with explicitly passed parameters in their original order
        # kwargs preserves the order the user wrote the parameters in Python 3.7+
        interface_config = {}
        for key, value in kwargs.items():
            interface_config[key] = value
        
        # Extract values with defaults
        endpoint = kwargs.get('endpoint', None)
        use_same_origin = kwargs.get('use_same_origin', False)
        origin_path = kwargs.get('origin_path', "/chat")
        origin_port = kwargs.get('origin_port', None)
        logging_enabled = kwargs.get('logging_enabled', False)
        log_file = kwargs.get('log_file', None)
        history_file = kwargs.get('history_file', None)
        aws_config = kwargs.get('aws_config', None)
        provider = kwargs.get('provider', DEFAULT_PROVIDER)
        provider_config = kwargs.get('provider_config', None)
        preface = kwargs.get('preface', None)
        conclusion = kwargs.get('conclusion', None)
        
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
                              preface,
                              conclusion,
                              interface_config)

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
                         preface: Optional[Union[str, Dict[str, Any]]] = None,
                         conclusion: Optional[str] = None,
                         interface_config: Optional[Dict[str, Any]] = None) -> None:
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

            # Use passed interface configuration and add filtered provider config
            final_interface_config = interface_config.copy() if interface_config else {}
            
            # Add filtered provider config (remove secrets) if it was explicitly passed
            if 'provider_config' in final_interface_config and final_interface_config['provider_config']:
                original_provider_config = final_interface_config['provider_config']
                safe_provider_config = {
                    k: v for k, v in original_provider_config.items()
                    if k not in (
                        'api_key', 'aws_access_key_id',
                        'aws_secret_access_key', 'aws_session_token'
                    )
                }
                if safe_provider_config:
                    final_interface_config['provider_config'] = safe_provider_config
                else:
                    # Remove provider_config if it only contained secrets
                    del final_interface_config['provider_config']
                    
                # Log (safe) provider config
                if self.logger and safe_provider_config:
                    self.logger.debug(f"Using provider '{provider}' with config: {safe_provider_config}")

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
                conclusion_string=conclusion,
                interface_config=final_interface_config
            )

            # Initialize preface if provided
            if preface:
                if isinstance(preface, str):
                    # Simple string case
                    self.conv.preface.add_content(text=preface, border_color="green")
                elif isinstance(preface, dict):
                    # Dict case - validate and extract
                    text = preface.get("text")
                    if not text:
                        raise ValueError("preface dict must contain 'text' key")
                    
                    self.conv.preface.add_content(
                        text=text,
                        title=preface.get("title"),
                        border_color=preface.get("border_color", "green"),
                        display_type=preface.get("display_type", "panel")
                    )
                else:
                    raise TypeError("preface must be string or dict")

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
