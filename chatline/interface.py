# interface.py

import logging
import os
from typing import Callable, AsyncGenerator, Optional
from .terminal import Terminal
from .conversation import Conversation
from .animations import Animations
from .styles import Styles
from .stream import EmbeddedStream, RemoteStream

class Interface:
    def __init__(self, 
                 endpoint: Optional[str] = None,
                 generator_func: Optional[Callable[[str], AsyncGenerator[str, None]]] = None):
        """Initialize chat interface with either local or remote stream."""
        self._init_logging()
        try:
            self._init_components(endpoint, generator_func)
        except Exception as e:
            self.logger.error("Failed to initialize interface: %s", str(e))
            raise

    def _init_logging(self) -> None:
        """Set up logging configuration."""
        log_dir = os.path.join(os.path.dirname(__file__), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s',
            filename=os.path.join(log_dir, 'chat_debug.log')
        )
        
        self.logger = logging.getLogger(__name__)
        self.logger.debug("Logging initialized")

    def _init_components(self, endpoint: Optional[str],
                        generator_func: Optional[Callable]) -> None:
        """Initialize all interface components in dependency order."""
        # Initialize core display components
        self.terminal = Terminal(styles=None)
        self.styles = Styles(terminal=self.terminal)
        self.terminal.styles = self.styles
        self.animations = Animations(terminal=self.terminal, styles=self.styles)
        
        # Set up appropriate stream
        if endpoint:
            self.logger.info("Using remote stream: %s", endpoint)
            self.stream = RemoteStream(endpoint, logger=self.logger)
        else:
            self.logger.info("Using embedded stream")
            self.stream = EmbeddedStream(generator_func, logger=self.logger)
        
        self.generator = self.stream.get_generator()
        
        # Initialize conversation manager
        self.conversation = Conversation(
            terminal=self.terminal,
            generator_func=self.generator,
            styles=self.styles,
            animations_manager=self.animations
        )
        
        # Initial terminal setup
        self.terminal._clear_screen()
        self.terminal._hide_cursor()

    def preface(self, text: str, color: Optional[str] = None, 
                display_type: str = "panel") -> None:
        """Add preface text to be displayed before conversation."""
        try:
            self.conversation.preface(text, color, display_type)
            self.logger.debug("Added preface text: %.50s...", text)
        except Exception as e:
            self.logger.error("Error adding preface: %s", str(e))
            raise

    def start(self, system_msg: str = None, intro_msg: str = None) -> None:
        """Start the conversation."""
        try:
            self.logger.info("Starting conversation")
            self.conversation.start(system_msg, intro_msg)
        except KeyboardInterrupt:
            self.logger.info("Conversation interrupted by user")
            self._ensure_cleanup()
        except Exception as e:
            self.logger.error("Error in conversation: %s", str(e))
            self._ensure_cleanup()
            raise

    def _ensure_cleanup(self) -> None:
        """Ensure proper cleanup on exit."""
        self.terminal._show_cursor()