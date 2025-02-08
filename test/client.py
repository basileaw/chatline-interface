# client.py

import os
import sys
import argparse

# Add the project root to the Python module search path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from chatline import Interface

# Default messages for the chat interface
DEFAULT_MESSAGES = {
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

def parse_args():
    parser = argparse.ArgumentParser(description='ChatLine Interface')
    parser.add_argument('-e', '--endpoint', 
                       help='Remote endpoint URL (e.g., http://localhost:5000/chat)')
    parser.add_argument('--enable-logging', 
                       action='store_true', 
                       help='Enable logging output')
    parser.add_argument('--system-message',
                       help='Override default system message')
    parser.add_argument('--initial-message',
                       help='Override default initial user message')
    return parser.parse_args()

def main():
    args = parse_args()
    
    # Initialize chat interface
    chat = Interface(endpoint=args.endpoint, logging_enabled=args.enable_logging)
    
    # Add welcome message
    chat.preface("Welcome to ChatLine", color="WHITE")
    
    # Prepare messages, allowing command line overrides
    messages = {
        "system": args.system_message or DEFAULT_MESSAGES["system"],
        "user": args.initial_message or DEFAULT_MESSAGES["user"]
    }
    
    # Start the chat interface with messages
    chat.start(messages)

if __name__ == "__main__":
    main()