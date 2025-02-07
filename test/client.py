import os
import sys
# Insert the project root to sys.path to allow absolute imports.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import argparse
from chatline import Interface

def parse_args():
    parser = argparse.ArgumentParser(description='ChatLine Interface')
    parser.add_argument('-e', '--endpoint', help='Remote endpoint URL (e.g., http://localhost:5000/chat)')
    return parser.parse_args()

def main():
    args = parse_args()
    chat = Interface(endpoint=args.endpoint)
    chat.preface("Welcome to ChatLine", color="WHITE")
    chat.start()

if __name__ == "__main__":
    main()
