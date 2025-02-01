# interface.py

import logging
import os
from typing import Callable, AsyncGenerator, Optional
from .terminal import Terminal
from .conversation import Conversation
from .animations import Animations
from .styles import Styles
from .stream import Stream
from .generator import generate_stream

class Interface:
    def __init__(self, generator_func: Optional[Callable[[str], AsyncGenerator[str, None]]] = None):
        # Set up logging
        log_dir = os.path.join(os.path.dirname(__file__), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s',
            filename=os.path.join(log_dir, 'chat_debug.log')
        )
        
        # Initialize core components
        self.styles = Styles()
        self.terminal = Terminal(styles=self.styles)
        self.stream = Stream(styles=self.styles, terminal=self.terminal)
        self.animations = Animations(terminal=self.terminal, styles=self.styles)
        
        # Set up generator function
        self.generator = generator_func if generator_func else generate_stream
            
        # Initialize conversation
        self.conversation = Conversation(
            terminal=self.terminal,
            generator_func=self.generator,
            styles=self.styles,
            stream=self.stream,
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