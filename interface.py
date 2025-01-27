# interface.py

import asyncio
import logging
from typing import Optional, Protocol
from utilities import RealUtilities
from animations.dot_loader import AsyncDotLoader
from animations.reverse_stream import ReverseStreamer
from state.terminal import TerminalManager
from state.conversation import ConversationManager
from state.stream import TextProcessor
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

class ComponentFactory:
    def __init__(self, utilities: Utilities):
        self.utils = utilities
        
    def create_output_handler(self):
        return TextProcessor(self.utils)
        
    def create_dot_loader(self, prompt: str, output_handler: Optional[TextProcessor] = None,
                         no_animation: bool = False) -> AsyncDotLoader:
        return AsyncDotLoader(
            utilities=self.utils,
            prompt=prompt,
            adaptive_buffer=output_handler,  # Now using output_handler as the buffer
            output_handler=output_handler,
            no_animation=no_animation
        )
        
    def create_reverse_streamer(self) -> ReverseStreamer:
        return ReverseStreamer(self.utils)

# Initialize core components
utilities = RealUtilities()

# Initialize managers
terminal = TerminalManager(utilities)
factory = ComponentFactory(utilities)
conversation = ConversationManager(
    terminal=terminal,
    generator_func=generate_stream,
    component_factory=factory
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