# interface.py

import logging
import os
from typing import Callable, AsyncGenerator, Optional
from terminal import Terminal
from conversation import Conversation
from animations import Animations
from styles import Styles
from stream import Stream

class Interface:
    def __init__(self, generator_func: Callable[[str], AsyncGenerator[str, None]]):
        # Create logs directory if it doesn't exist
        log_dir = os.path.join(os.path.dirname(__file__), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        # Initialize logging with path relative to this file
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s',
            filename=os.path.join(log_dir, 'chat_debug.log')
        )

        # Initialize components in dependency order
        self.styles = Styles()  # No dependencies
        self.terminal = Terminal(
            styles=self.styles
        )
        self.stream = Stream(
            styles=self.styles,
            terminal=self.terminal
        )
        self.animations = Animations(
            terminal=self.terminal,
            styles=self.styles
        )
        self.conversation = Conversation(
            terminal=self.terminal,
            generator_func=generator_func,
            styles=self.styles,
            stream=self.stream,
            animations_manager=self.animations
        )

        # Initialize terminal state
        self.terminal._clear_screen()
        self.terminal._hide_cursor()

    def preface(self, text: str, color: Optional[str] = None) -> None:
        """Alias to conversation.print() for backwards compatibility."""
        self.conversation.preface(text, color)

    def start(self, system_msg: str = None, intro_msg: str = None) -> None:
        """Alias to conversation.start() for backwards compatibility."""
        self.conversation.start(system_msg, intro_msg)

if __name__ == "__main__":
    # Example import and usage
    from generator import generate_stream
    chat = Interface(generate_stream)
    
    # Example of using pre-conversation text
    chat.preface("Welcome to ChatLine")
    chat.preface("Type 'help' for available commands")
    
    chat.start()