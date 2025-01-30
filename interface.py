# interface.py

import asyncio
import logging
from typing import Protocol, Callable, AsyncGenerator
from terminal import TerminalManager
from conversation import ConversationManager
from text import TextProcessor
from animations import AnimationsManager

class ChatInterface:
    def __init__(self, generator_func: Callable[[str], AsyncGenerator[str, None]]):
        # Initialize logging
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s',
            filename='logs/chat_debug.log'
        )

        # Initialize core components - updated dependency chain
        self.text_processor = TextProcessor()  # No dependencies
        self.terminal = TerminalManager(self.text_processor)  # Depends on text_processor
        self.animations = AnimationsManager(self.terminal, self.text_processor)  # Depends on terminal and text_processor
        self.conversation = ConversationManager(
            terminal=self.terminal,
            generator_func=generator_func,
            text_processor=self.text_processor,
            animations_manager=self.animations
        )

    def start(self, system_msg: str = None, intro_msg: str = None):
        """Start the chat interface with optional custom system and intro messages."""
        asyncio.run(self._async_start(system_msg, intro_msg))
            
    async def _async_start(self, system_msg: str = None, intro_msg: str = None):
        """Delegate conversation handling to ConversationManager."""
        await self.conversation.run_conversation(system_msg, intro_msg)

if __name__ == "__main__":
    # Example import and usage
    from generator import generate_stream
    chat = ChatInterface(generate_stream)
    chat.start()