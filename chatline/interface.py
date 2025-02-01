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

    def preface(self, text: str, color: Optional[str] = None, 
                display_type: str = "panel") -> None:
        """Add text to be displayed before conversation starts.
        
        Args:
            text: The text to display before the conversation begins
            color: Optional color name (e.g., 'GREEN', 'BLUE', 'PINK')
            display_type: Display type ("text" or "panel", defaults to "panel")
        """
        self.conversation.preface(text, color, display_type)

    def start(self, system_msg: str = None, intro_msg: str = None) -> None:
        """Start the conversation with optional custom system and intro messages."""
        self.conversation.start(system_msg, intro_msg)

if __name__ == "__main__":
    # Example import and usage
    from generator import generate_stream
    chat = Interface(generate_stream)
    
    # Example of using pre-conversation text in a panel
    chat.preface("Welcome to ChatLine", color="BLUE")
    
    chat.start()