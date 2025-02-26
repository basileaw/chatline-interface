# client.py

import argparse
from chatline import Interface

def main():
    parser = argparse.ArgumentParser(description='ChatLine Interface')
    parser.add_argument('-e', '--endpoint',
        help='Remote endpoint URL for chat service')
    parser.add_argument('--enable-logging',
        action='store_true',
        help='Enable debug logging')
    parser.add_argument('--log-file',
        help='Log file path (use "-" for stdout)')
    
    args = parser.parse_args()
    
    # Initialize the interface
    chat = Interface(
        endpoint=args.endpoint, 
        logging_enabled=args.enable_logging,
        log_file=args.log_file
    )
    
    # Add a welcome message
    chat.preface("Welcome to ChatLine", title="Baze, Inc.", border_color="dim yellow")
    
    # Start the conversation with default messages
    # In embedded mode, library defaults will be used
    # In remote mode, server may provide its own defaults
    chat.start()

if __name__ == "__main__":
    main()