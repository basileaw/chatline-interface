# message_provider.py

import logging
import httpx
import asyncio
from .generator import generate_stream
from typing import Optional, Callable, AsyncGenerator, Dict, List, Iterator

logger = logging.getLogger("uvicorn")

class MessageProvider:
    """Base provider class that handles message generation."""
    def __init__(self, generator_func: Optional[Callable[[str], AsyncGenerator[str, None]]] = None):
        self.generator = generator_func if generator_func else generate_stream

    def get_generator(self) -> Callable:
        """Returns the generator function to be used by the conversation."""
        return self.generator

class RemoteProvider(MessageProvider):
    """Provider that handles communication with a remote endpoint."""
    def __init__(self, endpoint: str):
        super().__init__()
        self.endpoint = endpoint.rstrip('/')
        self.client = httpx.Client()  # Synchronous client!

    def stream_from_endpoint(self, messages: List[Dict[str, str]], **kwargs) -> Iterator[str]:
        """Streams responses from the remote endpoint synchronously."""
        try:
            with self.client.stream('POST', f"{self.endpoint}/stream", 
                                  json={'messages': messages, **kwargs}, timeout=30.0) as response:
                for line in response.iter_lines():
                    if line:
                        yield line
                yield 'data: [DONE]\n\n'
        except Exception as e:
            logger.error(f"Remote streaming error: {str(e)}")
            yield 'data: [ERROR]\n\n'

    def get_generator(self) -> Callable:
        """Returns the streaming function for remote endpoint."""
        return self.stream_from_endpoint