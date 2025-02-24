# client.py

import argparse
from chatline import Interface

# Example messages for our test client implementation
EXAMPLE_MESSAGES = {
    "system": (
        'Write in present tense. Write in third person. Use the following text styles:\n'
        '- "quotes" for dialogue\n'
        '- [Brackets...] for actions\n'
        '- underscores for emphasis\n'
        '- asterisks for bold text'
    ),
    "user": (
        """Write the line: "[The machine powers on and hums...]\n\n"""
        """Then, start a new, 25-word paragraph."""
        """Begin with a greeting from the machine itself: " "Hey there," " """
    )
}

def main():
    parser = argparse.ArgumentParser(description='ChatLine Interface')
    parser.add_argument('-e', '--endpoint',
        help='Remote endpoint URL for chat service')
    parser.add_argument('--enable-logging',
        action='store_true',
        help='Enable debug logging')
    parser.add_argument('--log-file',
        help='Log file path (use "-" for stdout)')
    parser.add_argument('--use-server-messages',
        action='store_true',
        help='In remote mode, use server-provided default messages')
    
    args = parser.parse_args()
    
    # Initialize the interface
    chat = Interface(
        endpoint=args.endpoint, 
        logging_enabled=args.enable_logging,
        log_file=args.log_file
    )
    
    # Add a welcome message
    chat.preface("Welcome to ChatLine", title="Baze, Inc.", border_color="dim yellow")
    
    # Start the conversation
    if args.use_server_messages and args.endpoint:
        # In remote mode with --use-server-messages, don't provide messages
        # The server will provide default messages
        print("Using server-provided default messages")
        chat.start()
    else:
        # Otherwise use our example messages
        chat.start(EXAMPLE_MESSAGES)

if __name__ == "__main__":
    main()