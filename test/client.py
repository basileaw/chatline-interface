# client.py

import os
import sys
import argparse

# Add the project root to the Python module search path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from chatline import Interface

# Example messages for testing
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
    parser = argparse.ArgumentParser(description='ChatLine Interface')
    parser.add_argument('-e', '--endpoint', help='Remote endpoint URL')
    parser.add_argument('--enable-logging', action='store_true')
    args = parser.parse_args()

    chat = Interface(endpoint=args.endpoint, logging_enabled=args.enable_logging)
    chat.preface("Welcome to ChatLine", color="WHITE")
    chat.start(MESSAGES)

if __name__ == "__main__":
    main()