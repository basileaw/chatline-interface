# interface.py

import asyncio
import logging
from typing import Protocol
from terminal import TerminalManager
from conversation import ConversationManager
from text import TextProcessor
from animations import AnimationsManager
from generator import generate_stream

# Initialize logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='logs/chat_debug.log'
)

# Initialize core components - updated dependency chain
text_processor = TextProcessor()  # No dependencies
terminal = TerminalManager(text_processor)  # Depends on text_processor
animations = AnimationsManager(terminal, text_processor)  # Depends on terminal and text_processor
conversation = ConversationManager(
    terminal=terminal,
    generator_func=generate_stream,
    text_processor=text_processor,
    animations_manager=animations
)

async def main():
    try:
        # Initial setup
        await terminal.clear()
        intro_msg = "Introduce yourself in 3 lines, 7 words each..."
        _, intro_styled, _ = await conversation.handle_intro(intro_msg)

        # Main loop
        while True:
            try:
                if user := await terminal.get_user_input():
                    if user.lower() == "retry":
                        _, intro_styled, _ = await conversation.handle_retry(intro_styled)
                    else:
                        _, intro_styled, _ = await conversation.handle_message(user, intro_styled)
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
        await terminal.update_display()
        terminal._show_cursor()  # Use terminal's internal method

if __name__ == "__main__":
    asyncio.run(main())