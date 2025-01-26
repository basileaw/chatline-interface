# interface.py

import asyncio
import time
import shutil
import logging
from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import FormattedText
from output_handler import OutputHandler
from generator import generate_stream
from painter import TextPainter, COLORS, FORMATS
from stream_handler import StreamHandler
from factories import StreamComponentFactory
from utilities import (
    clear_screen,
    write_and_flush,
    manage_cursor
)

# Set up logging
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(levelname)s - %(message)s',
                   filename='chat_debug.log')

async def main():
    try:
        logging.debug("Starting main()")
        clear_screen()  # Removed await since this is synchronous
        
        # Initialize core components
        logging.debug("Initializing components")
        text_painter = TextPainter(base_color=COLORS['GREEN'])
        output_handler = OutputHandler(text_painter)
        component_factory = StreamComponentFactory(text_painter)
        stream_handler = StreamHandler(generate_stream, component_factory)
        
        logging.debug("Starting intro message")
        intro_msg = "Introduce yourself in 3 lines, 7 words each..."
        _, intro_styled, _ = await stream_handler.handle_intro(intro_msg, output_handler)
        
        logging.debug("Starting main loop")
        while True:
            try:
                user = await stream_handler.get_input()
                if not user:
                    continue
                    
                if user.lower() == "retry":
                    _, intro_styled, _ = await stream_handler.handle_retry(
                        intro_styled, 
                        output_handler,
                        silent=stream_handler.state.is_last_message_silent
                    )
                else:
                    _, intro_styled, _ = await stream_handler.handle_message(
                        user, intro_styled, output_handler
                    )
            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except Exception as e:
                logging.error(f"Error in main loop: {str(e)}", exc_info=True)
                print(f"\nAn error occurred: {str(e)}")
                continue

    except Exception as e:
        logging.error(f"Critical error in main: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    finally:
        write_and_flush(FORMATS['RESET'])
        manage_cursor(True)