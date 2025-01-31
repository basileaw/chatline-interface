# interface.py

import logging
from typing import Callable, AsyncGenerator, List, Optional
from terminal import TerminalManager
from conversation import ConversationManager
from text import TextProcessor
from animations import AnimationsManager
from styles import Styles
from stream import Stream

class ChatInterface:
    def __init__(self, generator_func: Callable[[str], AsyncGenerator[str, None]]):
        # Initialize preconversation text storage
        self.preconversation_text: List[str] = []
        
        # Initialize logging
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s',
            filename='logs/chat_debug.log'
        )

        # Initialize style processors
        self.text_processor = TextProcessor()  # Legacy processor
        self.styles = Styles()  # New styles system
        
        # Initialize terminal with both processors
        self.terminal = TerminalManager(
            text_processor=self.text_processor,  # Legacy - will be removed in final phase
            styles=self.styles  # New - will be the only dependency in final phase
        )
        
        # Initialize stream after terminal
        self.stream = Stream(
            styles=self.styles,
            terminal=self.terminal
        )
        
        # Initialize animations with both processors
        self.animations = AnimationsManager(
            terminal=self.terminal,
            text_processor=self.text_processor,  # Legacy
            styles=self.styles,  # New
            stream=self.stream  # New
        )
        
        # Initialize conversation manager with all components
        self.conversation = ConversationManager(
            terminal=self.terminal,
            generator_func=generator_func,
            text_processor=self.text_processor,  # Legacy
            styles=self.styles,  # New
            stream=self.stream,  # New
            animations_manager=self.animations
        )

        # Initialize terminal state
        self.terminal._clear_screen()
        self.terminal._hide_cursor()

    def print(self, text: str, color: Optional[str] = None) -> None:
        """Store text to be displayed before conversation starts.
        
        This text will be included in the scrolling animations during the conversation.
        Each print adds a new line that will be displayed on its own line.
        
        Args:
            text: The text to display before the conversation begins
            color: Optional color name (e.g., 'GREEN', 'BLUE', 'PINK'). If None,
                  uses terminal default color
        """
        # Store both text and color preference
        self.preconversation_text.append((text + "\n", color))

    def start(self, system_msg: str = None, intro_msg: str = None) -> None:
        """Start the chat interface with optional custom system and intro messages.
        
        Args:
            system_msg: Optional custom system message to override default
            intro_msg: Optional custom intro message to override default
        """
        self.conversation.run_conversation(
            system_msg=system_msg,
            intro_msg=intro_msg,
            preconversation_text=self.preconversation_text
        )

if __name__ == "__main__":
    # Example import and usage
    from generator import generate_stream
    chat = ChatInterface(generate_stream)
    
    # Example of using pre-conversation text
    chat.print("Welcome to the Chat Interface")
    chat.print("Type 'help' for available commands")
    
    chat.start()