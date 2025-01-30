# interface.py

import asyncio
import logging
from typing import Protocol
from terminal import TerminalManager
from conversation import ConversationManager
from text import TextProcessor
from animations import AnimationsManager
from generator import generate_stream

class ChatInterface:
    def __init__(self):
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
            generator_func=generate_stream,
            text_processor=self.text_processor,
            animations_manager=self.animations
        )

    async def start(self, intro_msg: str):
        try:
            # Initial setup
            await self.terminal.clear()
            _, intro_styled, _ = await self.conversation.handle_intro(intro_msg)

            # Main loop
            while True:
                try:
                    if user := await self.terminal.get_user_input():
                        if user.lower() == "retry":
                            _, intro_styled, _ = await self.conversation.handle_retry(intro_styled)
                        else:
                            _, intro_styled, _ = await self.conversation.handle_message(user, intro_styled)
                except KeyboardInterrupt:
                    print("\nExiting...")
                    break
                except Exception as e:
                    print(f"\nAn error occurred: {str(e)}")
                    logging.error(f"Error in main loop: {str(e)}", exc_info=True)
        except Exception as e:
            logging.error(f"Critical error in main: {str(e)}", exc_info=True)
            raise
        finally:
            await self.terminal.update_display()
            self.terminal._show_cursor()  # Use terminal's internal method

if __name__ == "__main__":
    chat = ChatInterface()
    asyncio.run(chat.start("Introduce yourself in 3 lines, 7 words each..."))