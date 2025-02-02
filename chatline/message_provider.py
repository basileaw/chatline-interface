# message_provider.py

import logging
from typing import Optional, Callable, AsyncGenerator
from .generator import generate_stream

class MessageProvider:
    def __init__(self, generator_func: Optional[Callable[[str], AsyncGenerator[str, None]]] = None):
        self.generator = generator_func if generator_func else generate_stream

    def get_generator(self) -> Callable:
        """Returns the generator function to be used by the conversation."""
        return self.generator