# interface.py

import asyncio
import logging
from typing import Protocol
from utilities import RealUtilities
from state.terminal import TerminalManager
from state.conversation import ConversationManager
from state.text import TextProcessor
from state.animations import AnimationsManager
from generator import generate_stream

# Initialize logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='logs/chat_debug.log'
)

class Utilities(Protocol):
    def clear_screen(self) -> None: ...
    def get_visible_length(self, text: str) -> int: ...
    def write_and_flush(self, text: str) -> None: ...
    def hide_cursor(self) -> None: ...
    def show_cursor(self) -> None: ...
    def get_terminal_width(self) -> int: ...
    def get_format(self, name: str) -> str: ...
    def get_base_color(self, color_name: str) -> str: ...
    def get_style(self, active_patterns: list[str], base_color: str) -> str: ...

# Initialize core components
utilities = RealUtilities()
terminal = TerminalManager(utilities)
animations = AnimationsManager(utilities)
text_processor = TextProcessor(utilities)
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
        utilities.show_cursor()

if __name__ == "__main__":
    asyncio.run(main())