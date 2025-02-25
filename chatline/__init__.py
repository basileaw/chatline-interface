# __init__.py

import sys, logging
import os, json
from datetime import datetime
from typing import Dict, Optional
from functools import partial

from .display import Display
from .stream import Stream
from .conversation import Conversation

# Default messages to use when none are provided by the developer
DEFAULT_MESSAGES = {
    "system": (
        'Write in present tense. Write in third person. Use the following text styles:\n'
        '- "quotes" for dialogue\n'
        '- [Brackets...] for actions\n'
        '- underscores for emphasis\n'
        '- asterisks for bold text\n\n'
        'Note: These are default instructions provided by the Chatline library.'
    ),
    "user": (
        '[Default message from Chatline]\n\n'
        'Please introduce yourself and explain how you can assist. '
        'Include an example of how you follow the style instructions above.'
    )
}

class Logger:
    """
    Custom logger that supports both standard logs
    and optional JSON conversation history logs.
    """

    def __init__(self, name: str, logging_enabled: bool = False, log_file: Optional[str] = None):
        """
        Args:
            name: The logger name.
            logging_enabled: If True, standard logging is turned on.
            log_file: If "-", logs go to stdout;
                      If None, logs go nowhere;
                      Otherwise logs go to the given file path.
        """
        self._logger = logging.getLogger(name)
        self._logger.propagate = False
        
        # Clear any existing handlers
        self._logger.handlers.clear()
        
        self.logging_enabled = logging_enabled
        self.log_file = log_file
        self.json_history_path = None

        # Standard logging setup
        if logging_enabled:
            # Decide how to log text-based messages
            if log_file == '-':
                handler = logging.StreamHandler(sys.stdout)
            elif log_file:
                handler = logging.FileHandler(log_file, mode='w')
            else:
                handler = logging.StreamHandler(sys.stderr)
            
            handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            
            self._logger.addHandler(handler)
            self._logger.setLevel(logging.DEBUG)

            # For conversation JSON logs, use a single file "conversation_history.json"
            # in the same directory as log_file (if it's not "-" or None).
            if log_file and log_file not in ("-", ""):
                log_dir = os.path.dirname(log_file) or "."
                os.makedirs(log_dir, exist_ok=True)
                # Always overwrite the same file each run
                self.json_history_path = os.path.join(log_dir, "conversation_history.json")
        else:
            # If logging is disabled, a NullHandler swallows logs
            self._logger.addHandler(logging.NullHandler())

        # Expose convenience methods like self.debug, self.info, self.error, ...
        for level in ['debug', 'info', 'warning', 'error']:
            setattr(self, level, partial(self._log, level))

    def _log(self, level: str, msg: str, exc_info: Optional[bool] = None) -> None:
        getattr(self._logger, level)(msg, exc_info=exc_info)

    def write_json(self, data):
        """
        Overwrite the entire conversation JSON file with 'data' each time.
        If self.json_history_path is None, do nothing.
        """
        if not self.json_history_path:
            return
        try:
            with open(self.json_history_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            self.error(f"Failed to write JSON history: {e}")


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
            self.stream = Stream.create(endpoint, logger=self.logger)

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

    def start(self, messages: Optional[Dict[str, str]] = None) -> None:
        """
        Start the conversation with optional messages.
        
        If no messages are provided, default messages will be used in both
        embedded and remote modes.
        
        Args:
            messages: Dictionary with 'system' and 'user' messages.
                     If None, default messages will be used.
        """
        if messages is None:
            self.logger.debug("No messages provided. Using default messages.")
            messages = DEFAULT_MESSAGES.copy()
        
        self.conv.actions.start_conversation(messages)