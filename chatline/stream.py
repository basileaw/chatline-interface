# stream.py

import httpx
from typing import Optional, Callable, AsyncGenerator, Dict, List, Protocol
from .generator import generate_stream

class Logger(Protocol):
    """Protocol defining the required logging interface."""
    def error(self, msg: str, *args, **kwargs) -> None: ...
    def debug(self, msg: str, *args, **kwargs) -> None: ...
    def info(self, msg: str, *args, **kwargs) -> None: ...

class Stream:
    """Base class for all stream providers."""
    def __init__(self, logger: Optional[Logger] = None):
        self.logger = logger

    def get_generator(self) -> Callable[[List[Dict[str, str]]], AsyncGenerator[str, None]]:
        """Must be implemented by subclasses to return their specific generator."""
        raise NotImplementedError

class EmbeddedStream(Stream):
    """Handles streaming from a local/embedded model."""
    def __init__(self, 
                 generator_func: Optional[Callable[[List[Dict[str, str]]], AsyncGenerator[str, None]]] = None,
                 logger: Optional[Logger] = None):
        super().__init__(logger=logger)
        self.generator = generator_func if generator_func else generate_stream
        if self.logger:
            self.logger.debug("Initialized EmbeddedStream with %s", 
                            "custom generator" if generator_func else "default generator")

    def get_generator(self) -> Callable[[List[Dict[str, str]]], AsyncGenerator[str, None]]:
        """Returns the configured generator function."""
        return self.generator

class RemoteStream(Stream):
    """Handles streaming from a remote endpoint."""
    def __init__(self, endpoint: str, logger: Optional[Logger] = None):
        super().__init__(logger=logger)
        self.endpoint = endpoint.rstrip('/')
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(30.0))
        if self.logger:
            self.logger.info(f"Initialized RemoteStream with endpoint: {self.endpoint}")

    async def stream_from_endpoint(self, 
                                 messages: List[Dict[str, str]], 
                                 **kwargs) -> AsyncGenerator[str, None]:
        """
        Stream response from remote endpoint with improved error handling.
        
        Args:
            messages: List of message dictionaries
            **kwargs: Additional parameters for the streaming request
            
        Yields:
            Formatted string chunks from the stream
        """
        try:
            async with self.client.stream('POST', 
                                        f"{self.endpoint}/stream", 
                                        json={'messages': messages, **kwargs},
                                        timeout=30.0) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        yield line
                yield 'data: [DONE]\n\n'

        except httpx.TimeoutError as e:
            if self.logger:
                self.logger.error(f"Stream timeout error: {str(e)}")
            yield 'data: [ERROR] Request timed out\n\n'
            
        except httpx.HTTPStatusError as e:
            if self.logger:
                self.logger.error(f"HTTP error {e.response.status_code}: {str(e)}")
            yield f'data: [ERROR] HTTP {e.response.status_code}\n\n'
            
        except httpx.RequestError as e:
            if self.logger:
                self.logger.error(f"Request error: {str(e)}")
            yield 'data: [ERROR] Failed to connect to endpoint\n\n'
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Unexpected streaming error: {str(e)}")
            yield f'data: [ERROR] {str(e)}\n\n'

    def get_generator(self) -> Callable[[List[Dict[str, str]]], AsyncGenerator[str, None]]:
        """Returns the stream_from_endpoint method as the generator."""
        return self.stream_from_endpoint

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with proper client cleanup."""
        try:
            await self.client.aclose()
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error closing client: {str(e)}")
            raise