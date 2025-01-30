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

    def start(self, intro_msg: str = None):
        asyncio.run(self._async_start(intro_msg))
            
    async def _async_start(self, intro_msg: str = None):
        try:
            await self.terminal.clear()
            _, intro_styled, _ = await self.conversation.handle_intro(
                intro_msg or "Introduce yourself in 3 lines, 7 words each..."
            )
            
            while True:
                if user := await self.terminal.get_user_input():
                    try:
                        _, intro_styled, _ = await self.conversation.handle_retry(intro_styled) if user.lower() == "retry" \
                            else await self.conversation.handle_message(user, intro_styled)
                    except Exception as e:
                        logging.error(f"Error processing message: {str(e)}", exc_info=True)
                        print(f"\nAn error occurred: {str(e)}")
        except KeyboardInterrupt:
            print("\nExiting...")
        except Exception as e:
            logging.error(f"Critical error: {str(e)}", exc_info=True)
            raise
        finally:
            await self.terminal.update_display()
            self.terminal._show_cursor()

if __name__ == "__main__":
    # Example import and usage
    from generator import generate_stream
    chat = ChatInterface(generate_stream)
    chat.start()  