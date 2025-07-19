# client.py

import argparse
from chatline import Interface


def main():
    parser = argparse.ArgumentParser(description="ChatLine Interface")
    parser.add_argument("-e", "--endpoint", help="Remote endpoint URL for chat service")
    parser.add_argument(
        "--same-origin",
        action="store_true",
        help="Auto-detect server running on the same host",
    )
    parser.add_argument(
        "--origin-path",
        default="/chat",
        help="Path component for same-origin server (default: /chat)",
    )
    parser.add_argument(
        "--origin-port", type=int, help="Port fora same-origin server (default: 8000)"
    )
    parser.add_argument(
        "--enable-logging", action="store_true", help="Enable debug logging"
    )
    parser.add_argument("--log-file", help='Log file path (use "-" for stdout)')

    args = parser.parse_args()

    # Initialize the interface
    chat = Interface(
        endpoint=args.endpoint,
        use_same_origin=args.same_origin,
        origin_path=args.origin_path,
        origin_port=args.origin_port,
        logging_enabled=args.enable_logging,
        log_file=args.log_file,
        # preface={
        #     "text": "Welcome to ChatLine",
        #     "title": "Baze, Inc.",
        #     "border_color": "dim yellow"
        # }
        loading_message="Testing 123",
    )

    # Start the conversation with default messages
    # In embedded mode, library defaults will be used
    # In remote mode, server may provide its own defaults
    chat.start()


if __name__ == "__main__":
    main()
