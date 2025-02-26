# default_messages.py

# Default messages to use when none are provided by the developer
# Using array format for direct use in both frontend and backend
DEFAULT_MESSAGES = [
    {
        "role": "system",
        "content": (
            'Write in present tense. Write in third person. Use the following text styles:\n'
            '- "quotes" for dialogue\n'
            '- [Brackets...] for actions\n'
            '- underscores for emphasis\n'
            '- asterisks for bold text\n'
        )
    },
    {
        "role": "user",
        "content": (
            'Write the line: \"[The machine powers on and hums...]\n\nThen, start a new, 25-word paragraph, informing me that I have not provided any messages, so the system defaults are being used. Begin this paragraph with a greeting from the machine itself: \" \"Hey there,\" \" \n\n'
        )
    }
]