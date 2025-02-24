import sys
from chatline import Interface

# Set up logging to console for immediate feedback
import logging
logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)

# Your test messages
MESSAGES = {
    "system": "You are a helpful assistant.",
    "user": "Hello, how are you?"
}

# Create and run the interface
try:
    print("Creating Interface...")
    chat = Interface(
        endpoint="http://127.0.0.1:8000/chat", 
        logging_enabled=True,
        log_file="-"  # Log to stdout
    )
    
    print("Setting preface...")
    chat.preface("Test Chatline", title="Debug Test")
    
    print("Starting conversation...")
    chat.start(MESSAGES)
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()