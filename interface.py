import asyncio
import logging
from typing import Optional, Protocol, Callable, Dict, Any
from utilities import RealUtilities
from stream.painter import TextPainter
from stream.printer import OutputHandler
from stream.buffer import AsyncAdaptiveBuffer
from animations.dot_loader import AsyncDotLoader
from animations.reverse_stream import ReverseStreamer
from state.terminal import TerminalManager
from state.conversation import ConversationManager
from generator import generate_stream

class Utilities(Protocol):
    def clear_screen(self) -> None: ...
    def get_visible_length(self, text: str) -> int: ...
    def write_and_flush(self, text: str) -> None: ...
    def hide_cursor(self) -> None: ...
    def show_cursor(self) -> None: ...
    def get_terminal_width(self) -> int: ...

class Painter(Protocol):
    def get_format(self, name: str) -> str: ...
    def get_color(self, name: str) -> str: ...
    @property
    def base_color(self) -> str: ...
    def process_chunk(self, text: str) -> str: ...
    def reset(self) -> None: ...

# Initialize logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='chat_debug.log'
)

class ComponentFactory:
    def __init__(self, utilities: Utilities, painter: Painter):
        self.utils = utilities
        self.painter = painter
        
    def create_output_handler(self) -> OutputHandler:
        return OutputHandler(self.painter, self.utils)
        
    def create_adaptive_buffer(self) -> AsyncAdaptiveBuffer:
        return AsyncAdaptiveBuffer()
        
    def create_dot_loader(self, prompt: str, output_handler: Optional[OutputHandler] = None,
                         no_animation: bool = False) -> AsyncDotLoader:
        return AsyncDotLoader(
            utilities=self.utils,
            prompt=prompt,
            adaptive_buffer=self.create_adaptive_buffer(),
            output_handler=output_handler,
            no_animation=no_animation
        )
        
    def create_reverse_streamer(self) -> ReverseStreamer:
        return ReverseStreamer(self.utils, self.painter)

# Initialize core components
utilities = RealUtilities()
painter = TextPainter(utilities=utilities)

# Initialize managers
terminal = TerminalManager(utilities, painter)
factory = ComponentFactory(utilities, painter)
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
        utilities.write_and_flush(painter.get_format('RESET'))
        utilities.show_cursor()

if __name__ == "__main__":
    asyncio.run(main())