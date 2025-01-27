import asyncio
import logging
from typing import Protocol
from utilities import RealUtilities
from streaming_output.painter import TextPainter
from generator import generate_stream
from factories import StreamComponentFactory

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='chat_debug.log'
)

async def main():
    try:
        logging.debug("Starting main()")
        
        # Create core dependencies
        utilities = RealUtilities()
        painter = TextPainter(utilities=utilities)
        logging.debug("Created core dependencies")
        
        # Create factory with core dependencies
        component_factory = StreamComponentFactory(
            utilities=utilities,
            painter=painter
        )
        component_factory.set_generator(generate_stream)
        logging.debug("Created component factory")
        
        # Get managers from factory
        terminal = component_factory.terminal_manager
        conversation = component_factory.conversation_manager
        logging.debug("Got managers from factory")
        
        # Clear screen using terminal manager
        await terminal.clear()
        logging.debug("Cleared screen")
        
        # Initial message handling
        logging.debug("About to start intro message")
        intro_msg = "Introduce yourself in 3 lines, 7 words each..."
        _, intro_styled, _ = await conversation.handle_intro(intro_msg)
        logging.debug("Completed intro handling")
        
        logging.debug("Starting main loop")
        while True:
            try:
                logging.debug("Waiting for user input")
                user = await terminal.get_user_input()
                logging.debug(f"Got user input: {user}")
                
                if not user:
                    continue
                    
                if user.lower() == "retry":
                    logging.debug("Handling retry")
                    _, intro_styled, _ = await conversation.handle_retry(intro_styled)
                else:
                    logging.debug("Handling message")
                    _, intro_styled, _ = await conversation.handle_message(user, intro_styled)
                    
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
        # Clean up using terminal manager
        await terminal.update_display()
        utilities.write_and_flush(painter.get_format('RESET'))
        utilities.show_cursor()
        
if __name__ == "__main__":
    asyncio.run(main())