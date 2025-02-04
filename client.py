# test_client.py

import argparse
from chatline import Interface

def parse_args():
    parser = argparse.ArgumentParser(description='ChatLine Inrterface')
    parser.add_argument('-e', '--endpoint', 
                       help='Remote endpoint URL (e.g., http://localhost:5000/chat)')
    return parser.parse_args()

def main():
    args = parse_args()
    chat = Interface(endpoint=args.endpoint)
    chat.preface("Welcome to ChatLine", color="WHITE")
    chat.start()

if __name__ == "__main__":
    main()