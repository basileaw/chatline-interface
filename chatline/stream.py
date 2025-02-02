# stream.py

import httpx
from typing import Optional, Callable, AsyncGenerator, Dict, List, Any
from .generator import generate_stream

class Stream:
    """
    Base class for all stream providers. Handles the generation of message streams,
    whether from an embedded model or remote endpoint.
    """
    def __init__(self, logger: Any = None):
        self.logger = logger

    def get_generator(self) -> Callable:
        """Must be implemented by subclasses to return their specific generator."""
        raise NotImplementedError

class EmbeddedStream(Stream):
    """Handles streaming from a local/embedded model."""
    def __init__(self, generator_func: Optional[Callable[[str], AsyncGenerator[str, None]]] = None,
                 logger: Any = None):
        super().__init__(logger=logger)
        self.generator = generator_func if generator_func else generate_stream

    def get_generator(self) -> Callable:
        return self.generator

class RemoteStream(Stream):
    """Handles streaming from a remote endpoint."""
    def __init__(self, endpoint: str, logger: Any = None):
        super().__init__(logger=logger)
        self.endpoint = endpoint.rstrip('/')
        self.client = httpx.AsyncClient()

    async def stream_from_endpoint(self, messages: List[Dict[str, str]], **kwargs) -> AsyncGenerator[str, None]:
        try:
            async with self.client.stream('POST', f"{self.endpoint}/stream", 
                                     json={'messages': messages, **kwargs}) as response:
                async for line in response.aiter_lines():
                    if line:
                        yield line
                yield 'data: [DONE]\n\n'
        except Exception as e:
            if self.logger:
                self.logger.error(f"Remote streaming error: {str(e)}")
            yield 'data: [ERROR]\n\n'

    def get_generator(self) -> Callable:
        return self.stream_from_endpoint

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()