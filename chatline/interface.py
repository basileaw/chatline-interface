# interface.py

import logging
import os
import argparse
from typing import Callable, AsyncGenerator, Optional
from terminal import Terminal
from conversation import Conversation
from animations import Animations
from styles import Styles
from stream import Stream
from remote import RemoteGenerator
from generator import generate_stream

class Interface:
    @classmethod
    def from_args(cls) -> 'Interface':
        """Create an Interface instance from command line arguments."""
        parser = argparse.ArgumentParser(description='ChatLine interface')
        parser.add_argument('-e', '--endpoint', 
                          help='Chat endpoint URL or path (e.g., http://localhost:8000/chat or /chat)')
        args = parser.parse_args()
        
        return cls(endpoint=args.endpoint) if args.endpoint else cls()

    def __init__(self, endpoint: Optional[str] = None, 
                 generator_func: Optional[Callable[[str], AsyncGenerator[str, None]]] = None):
        """
        Initialize the chat interface.
        
        Args:
            endpoint (str, optional): Remote endpoint URL or path
            generator_func (callable, optional): Custom generator function
        """
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
        if generator_func:
            self.generator = generator_func
        elif endpoint:
            self.generator = RemoteGenerator(endpoint)
        else:
            self.generator = generate_stream
            
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

if __name__ == "__main__":
    chat = Interface.from_args()
    chat.preface("Welcome to ChatLine", color="BLUE")
    chat.start()