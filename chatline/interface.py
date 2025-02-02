# interface.py

import logging
import os
from typing import Callable, AsyncGenerator, Optional, Union
from .terminal import Terminal
from .conversation import Conversation
from .animations import Animations
from .styles import Styles
from .stream import EmbeddedStream, RemoteStream

class Interface:
    def __init__(self, 
                 endpoint: Optional[str] = None,
                 generator_func: Optional[Callable[[str], AsyncGenerator[str, None]]] = None):
        # Set up logging
        self._setup_logging()
        
        # Initialize core components in dependency order
        self.logger.debug("Initializing interface components")
        try:
            self._init_components(endpoint, generator_func)
        except Exception as e:
            self.logger.error(f"Failed to initialize interface: {str(e)}")
            raise

    def _setup_logging(self) -> None:
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

    def _init_components(self, 
                        endpoint: Optional[str],
                        generator_func: Optional[Callable[[str], AsyncGenerator[str, None]]]) -> None:
        """Initialize all components in the correct order."""
        # Terminal and styles are interdependent
        self.terminal = Terminal(styles=None)  # Temporarily None
        self.styles = Styles(terminal=self.terminal)
        self.terminal.styles = self.styles
        
        # Animations depend on terminal and styles
        self.animations = Animations(terminal=self.terminal, styles=self.styles)
        
        # Initialize stream based on configuration
        if endpoint:
            self.logger.info(f"Using remote stream with endpoint: {endpoint}")
            self.stream = RemoteStream(endpoint, logger=self.logger)
        else:
            self.logger.info("Using embedded stream with generator function")
            self.stream = EmbeddedStream(generator_func, logger=self.logger)
            
        self.generator = self.stream.get_generator()
            
        # Initialize conversation last as it depends on all other components
        self.conversation = Conversation(
            terminal=self.terminal,
            generator_func=self.generator,
            styles=self.styles,
            animations_manager=self.animations
        )
        
        # Clear screen and hide cursor initially
        self.terminal._clear_screen()
        self.terminal._hide_cursor()
        
        self.logger.debug("All components initialized successfully")

    def preface(self, text: str, color: Optional[str] = None, display_type: str = "panel") -> None:
        """Add text to be displayed before conversation starts."""
        try:
            self.conversation.preface(text, color, display_type)
            self.logger.debug(f"Added preface text: {text[:50]}...")
        except Exception as e:
            self.logger.error(f"Error adding preface: {str(e)}")
            raise

    def start(self, system_msg: str = None, intro_msg: str = None) -> None:
        """Start the conversation with optional system and intro messages."""
        try:
            self.logger.info("Starting conversation")
            self.conversation.start(system_msg, intro_msg)
        except KeyboardInterrupt:
            self.logger.info("Conversation interrupted by user")
            self.terminal._show_cursor()  # Ensure cursor is visible on interrupt
        except Exception as e:
            self.logger.error(f"Error starting conversation: {str(e)}")
            self.terminal._show_cursor()  # Ensure cursor is visible on error
            raise