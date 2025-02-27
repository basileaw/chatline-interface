Aan easy-to-use, pretty, command-line chat interface for AWS Bedrock with simple animations, text styling, and 

![PyPI](https://img.shields.io/pypi/v/chatline.svg) ![License](https://img.shields.io/github/license/anotherbazeinthewall/chatline-interface.svg) ![Used on chat.alexbasile.com](https://img.shields.io/badge/Used%20on-chat.alexbasile.com-blue?style=flat&logo=google-chrome)


## Installation

Install it from PyPI using your favorite package manager:  
```
pip install chatline
```
## Config 

### Embedded Stream: 

The most basic config simply passes a system and user message to the embedded stream, using your pre-configured AWS defaults:

```
from chatline import Interface

def main():
    # Initialize the interface in embedded mode (no endpoint)
    chat = Interface()
    
    # Start the conversation with default messages
    chat.start()

if __name__ == "__main__":
    main()

```
While some additional args can configure an introductory panel and logging:
```
from chatline import Interface

def main():
    # Initialize the interface in embedded mode with logging enabled
    chat = Interface(
        logging_enabled=True,
        log_file="logs/chatline_debug.log"
    )
    
    # Add a welcome message
    chat.preface("Welcome to ChatLine", title="Baze, Inc.", border_color="dim yellow")
    
    # Start the conversation with default messages
    chat.start()

if __name__ == "__main__":
    main()
```

### Remote Stream: 

Alternatively, you can use chatline in your server and 

## Controls 

Return to 'Send' (send the current message)
Crt + R to 'Retry' (generate a new response to the previous message)
Crtl + E to 'Edit' (edit the previous message before sending it again)
