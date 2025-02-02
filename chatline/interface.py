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
        log_dir = os.path.join(os.path.dirname(__file__), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s',
            filename=os.path.join(log_dir, 'chat_debug.log')
        )
        
        self.logger = logging.getLogger(__name__)
        
        # Initialize core components
        self.terminal = Terminal(styles=None)  # Temporarily None
        self.styles = Styles(terminal=self.terminal)
        self.terminal.styles = self.styles
        self.animations = Animations(terminal=self.terminal, styles=self.styles)
        
        # Set up stream based on configuration
        if endpoint:
            self.stream = RemoteStream(endpoint, logger=self.logger)
        else:
            self.stream = EmbeddedStream(generator_func, logger=self.logger)
            
        self.generator = self.stream.get_generator()
            
        # Initialize conversation
        self.conversation = Conversation(
            terminal=self.terminal,
            generator_func=self.generator,
            styles=self.styles,
            animations_manager=self.animations
        )
        
        self.terminal._clear_screen()
        self.terminal._hide_cursor()

    def preface(self, text: str, color: Optional[str] = None, display_type: str = "panel") -> None:
        """Add text to be displayed before conversation starts."""
        self.conversation.preface(text, color, display_type)

    def start(self, system_msg: str = None, intro_msg: str = None) -> None:
        """Start the conversation with optional system and intro messages."""
        self.conversation.start(system_msg, intro_msg)