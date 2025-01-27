# interface.py

import asyncio
import logging
from typing import Protocol
from utilities import RealUtilities
from streaming_output.painter import TextPainter
from generator import generate_stream
from state_managers.stream import StreamHandler
from state_managers.conversation import ConversationState
from factories import StreamComponentFactory

# Set up logging
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(levelname)s - %(message)s',
                   filename='chat_debug.log')

async def main():
    try:
        logging.debug("Starting main()")
        
        # Create core dependencies
        utilities = RealUtilities()
        painter = TextPainter(utilities=utilities)
        
        # Create factory with core dependencies
        component_factory = StreamComponentFactory(
            utilities=utilities,
            painter=painter
        )
        
        # Create output handler through factory
        output_handler = component_factory.create_output_handler()
        
        # Create conversation state
        conversation_state = ConversationState(
            system_prompt='Be helpful, concise, and honest. Use text styles:\n'
            '- "quotes" for dialogue\n'
            '- [brackets] for observations\n'
            '- _underscores_ for emphasis\n'
            '- *asterisks* for bold text'
        )
        
        # Create stream handler with dependencies
        stream_handler = StreamHandler(
            utilities=utilities,
            generator_func=generate_stream,
            component_factory=component_factory,
            conversation_state=conversation_state
        )
        
        # Clear screen using utilities
        utilities.clear_screen()
        
        # Initial message handling
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

    finally:
        # Clean up using painter and utilities
        utilities.write_and_flush(painter.get_format('RESET'))
        utilities.show_cursor()

if __name__ == "__main__":
    asyncio.run(main())