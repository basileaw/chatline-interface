# stream.py

import httpx
from .generator import generate_stream

class Stream:
    def __init__(self, logger=None):
        self.logger = logger

    def get_generator(self):
        raise NotImplementedError

class EmbeddedStream(Stream):
    def __init__(self, generator_func=None, logger=None):
        super().__init__(logger=logger)
        self.generator = generator_func if generator_func else generate_stream
        if self.logger:
            self.logger.debug("Initialized %s generator", "custom" if generator_func else "default")

    def get_generator(self):
        return self.generator

class RemoteStream(Stream):
    def __init__(self, endpoint, logger=None):
        super().__init__(logger=logger)
        self.endpoint = endpoint.rstrip('/')
        self.client = httpx.AsyncClient(timeout=30.0)
        if self.logger:
            self.logger.debug("Initialized remote stream: %s", self.endpoint)

    async def stream_from_endpoint(self, messages, **kwargs):
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
            yield f'data: [ERROR] Request timed out\n\n'
            
        except httpx.HTTPStatusError as e:
            if self.logger:
                self.logger.error("HTTP %d: %s", e.response.status_code, str(e))
            yield f'data: [ERROR] HTTP {e.response.status_code}\n\n'
            
        except httpx.RequestError as e:
            if self.logger:
                self.logger.error("Connection error: %s", str(e))
            yield 'data: [ERROR] Failed to connect\n\n'
            
        except Exception as e:
            if self.logger:
                self.logger.error("Unexpected error: %s", str(e))
            yield f'data: [ERROR] {str(e)}\n\n'

    def get_generator(self):
        return self.stream_from_endpoint

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()