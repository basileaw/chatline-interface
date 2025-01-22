# stream_handler.py
import asyncio
from dot_loader import DotLoader

class StreamHandler:
    def __init__(self, generator_func):
        self.generator_func = generator_func

    async def stream_message(self, conversation, prompt_line):
        """Stream a message using the configured generator function."""
        loader = DotLoader(prompt_line)
        stream = self.generator_func(conversation)
        return await loader.run_with_loading(stream)