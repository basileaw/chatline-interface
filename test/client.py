import os
import sys
import argparse

# Add the project root to the Python module search path.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from chatline import Interface

def parse_args():
    parser = argparse.ArgumentParser(description='ChatLine Interface')
    parser.add_argument(
        '-e', '--endpoint', 
        help='Remote endpoint URL (e.g., http://localhost:5000/chat)'
    )
    parser.add_argument(
        '--enable-logging', 
        action='store_true', 
        help='Enable logging output'
    )
    return parser.parse_args()

def main():
    args = parse_args()
    # Pass the logging flag to the Interface
    chat = Interface(endpoint=args.endpoint, logging_enabled=args.enable_logging)
    chat.preface("Welcome to ChatLine", color="WHITE")
    chat.start()

if __name__ == "__main__":
    main()
