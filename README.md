Aan easy-to-use, pretty, command-line chat interface for AWS Bedrock with simple animations, text styling, and 

![PyPI](https://img.shields.io/pypi/v/chatline.svg) ![License](https://img.shields.io/github/license/my-username/my-repo.svg)

## Installation

Install it straight from the repo: 
```
pip install git+https://github.com/anotherbazeinthewall/chatline-interface.git
```
## Config 

### Embedded Stream: 

The most basic config simply passes a system and user message to the embedded stream, using your pre-configured AWS defaults:

```
from chatline import Interface

MESSAGES = {
    "system": (
        'Be cool.'
    ),
    "user": (
        """Introduce yourself to me in 25 words"""
    )
}

chat = Interface()
chat.start(MESSAGES)

```

### Remote Stream: 

Alternatively, you can use chatline in your server and 

## Controls 

Return to 'Send' (send the current message)
Crt + R to 'Retry' (generate a new response to the previous message)
Crtl + E to 'Edit' (edit the previous message before sending it again)
