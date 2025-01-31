# interface.py

import logging
from typing import Callable, AsyncGenerator, List, Optional
from terminal import Terminal
from conversation import Conversation
from animations import Animations
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