# stream.py

import httpx
from typing import Optional, Callable, AsyncGenerator, Dict, List, Protocol
from .generator import generate_stream

class Logger(Protocol):
    """Protocol for logger interface."""
    def error(self, msg: str, *args, **kwargs) -> None: ...
    def debug(self, msg: str, *args, **kwargs) -> None: ...

class StreamError(Exception):
    """Base exception for stream errors."""
    pass

class Stream:
    """Base stream provider class."""
    def __init__(self, logger: Optional[Logger] = None):
        self.logger = logger

    def get_generator(self) -> Callable[[List[Dict[str, str]]], AsyncGenerator[str, None]]:
        """Get message generator function."""
        raise NotImplementedError

class EmbeddedStream(Stream):
    """Local/embedded model stream handler."""
    def __init__(self, 
                 generator_func: Optional[Callable[[List[Dict[str, str]]], AsyncGenerator[str, None]]] = None,
                 logger: Optional[Logger] = None):
        super().__init__(logger=logger)
        self.generator = generator_func if generator_func else generate_stream
        
        if self.logger:
            self.logger.debug("Initialized embedded stream %s", 
                            "with custom generator" if generator_func else "with default generator")

    def get_generator(self) -> Callable[[List[Dict[str, str]]], AsyncGenerator[str, None]]:
        return self.generator

class RemoteStream(Stream):
    """Remote endpoint stream handler."""
    def __init__(self, endpoint: str, logger: Optional[Logger] = None):
        super().__init__(logger=logger)
        self.endpoint = endpoint.rstrip('/')
        self.client = httpx.AsyncClient(timeout=30.0)
        
        if self.logger:
            self.logger.debug("Initialized remote stream with endpoint: %s", self.endpoint)

    async def stream_from_endpoint(self, 
                                 messages: List[Dict[str, str]], 
                                 **kwargs) -> AsyncGenerator[str, None]:
        """Stream from remote endpoint with robust error handling."""
        try:
            async with self.client.stream(
                'POST',
                f"{self.endpoint}/stream",
                json={'messages': messages, **kwargs},
                timeout=30.0
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        yield line
                yield 'data: [DONE]\n\n'

        except httpx.TimeoutError as e:
            if self.logger:
                self.logger.error("Stream timeout: %s", str(e))
            yield self._format_error("Request timed out")
            
        except httpx.HTTPStatusError as e:
            if self.logger:
                self.logger.error("HTTP error %d: %s", e.response.status_code, str(e))
            yield self._format_error(f"HTTP {e.response.status_code}")
            
        except httpx.RequestError as e:
            if self.logger:
                self.logger.error("Connection error: %s", str(e))
            yield self._format_error("Failed to connect to endpoint")
            
        except Exception as e:
            if self.logger:
                self.logger.error("Unexpected error: %s", str(e))
            yield self._format_error(str(e))

    def _format_error(self, message: str) -> str:
        """Format error message for stream output."""
        return f'data: [ERROR] {message}\n\n'

    def get_generator(self) -> Callable[[List[Dict[str, str]]], AsyncGenerator[str, None]]:
        return self.stream_from_endpoint

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()