# client.py

import argparse
from chatline import Interface

# Example messages for our test client implementation
MESSAGES = {
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
    # Parse command line arguments for endpoint configuration and logging
    parser = argparse.ArgumentParser(description='ChatLine Interface')
    parser.add_argument('-e', '--endpoint', 
                       help='Remote endpoint URL for chat service')
    parser.add_argument('--enable-logging', 
                       action='store_true',
                       help='Enable debug logging')
    args = parser.parse_args()

    # Initialize and start the chat interface
    chat = Interface(endpoint=args.endpoint, logging_enabled=args.enable_logging)
    chat.preface("Welcome to ChatLine", color="WHITE")
    chat.start(MESSAGES)

if __name__ == "__main__":
    main()