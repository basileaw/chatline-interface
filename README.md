An extremely simple command line interface for AWS Bedrock LLM chat.

## Usage 

The absolute simplest, most basic usage is as follows:

```
from chatline import Interface

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

chat = Interface()
chat.preface("Welcome to ChatLine", color="WHITE")
chat.start(MESSAGES)

```