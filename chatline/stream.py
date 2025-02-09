# stream.py

import httpx
import json
from typing import Optional, Dict, Any, AsyncGenerator, Callable
from .generator import generate_stream

class Stream:
    """Base class for handling message streaming."""
    
    def __init__(self, logger=None):
        self.logger = logger
        self._last_error: Optional[str] = None

    @classmethod 
    def create(cls, endpoint: Optional[str] = None, logger=None) -> 'Stream':
        if endpoint:
            return RemoteStream(endpoint, logger=logger)
        return EmbeddedStream(logger=logger)

    def get_generator(self) -> Callable:
        """Abstract method to get the generator function"""
        raise NotImplementedError

class EmbeddedStream(Stream):
    """Handler for local embedded message streams."""
    
    def __init__(self, logger=None):
        super().__init__(logger=logger)
        self.generator = generate_stream
        if self.logger:
            self.logger.debug("Initialized embedded stream with default generator")

    async def _wrap_generator(self, generator_func: Callable, messages: list, state: Optional[Dict] = None, **kwargs) -> AsyncGenerator[str, None]:
        """Helper method to wrap generator with error handling and logging"""
        try:
            if self.logger:
                self.logger.debug(f"Starting generator with {len(messages)} messages")
                if state:
                    self.logger.debug(f"Current conversation state: turn={state.get('turn_number', 0)}")

            async for chunk in generator_func(messages, **kwargs):
                if self.logger:
                    self.logger.debug(f"Generated chunk: {chunk[:50]}...")
                yield chunk

        except Exception as e:
            error_msg = f"Generator error: {str(e)}"
            if self.logger:
                self.logger.error(error_msg)
            self._last_error = str(e)
            yield f"Error during generation: {str(e)}"

    def get_generator(self) -> Callable:
        async def generator_wrapper(messages: list, state: Optional[Dict] = None, **kwargs):
            try:
                if state and self.logger:
                    self.logger.debug(f"Processing embedded stream with state: turn={state.get('turn_number', 0)}")

                async for chunk in self._wrap_generator(self.generator, messages, state, **kwargs):
                    yield chunk

            except Exception as e:
                if self.logger:
                    self.logger.error(f"Embedded stream error: {str(e)}")
                self._last_error = str(e)
                yield f"Error in embedded stream: {str(e)}"

        return generator_wrapper

class RemoteStream(Stream):
    """Handler for remote message streams."""
    
    def __init__(self, endpoint: str, logger=None):
        super().__init__(logger=logger)
        self.endpoint = endpoint.rstrip('/')
        self.client = httpx.AsyncClient(timeout=30.0)
        if self.logger:
            self.logger.debug(f"Initialized remote stream: {self.endpoint}")

    async def _stream_from_endpoint(self, messages: list, state: Optional[Dict] = None, **kwargs) -> AsyncGenerator[str, None]:
        try:
            if self.logger:
                self.logger.debug(f"Starting remote stream request with {len(messages)} messages")

            payload = {
                'messages': messages,
                'conversation_state': state,
                **kwargs
            }

            async with self.client.stream(
                'POST',
                self.endpoint,
                json=payload,
                timeout=30.0
            ) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if line:
                        if self.logger:
                            self.logger.debug(f"Remote response chunk: {line[:50]}...")
                        yield line

                if response.headers.get('X-Conversation-State'):
                    try:
                        new_state = json.loads(response.headers['X-Conversation-State'])
                        if self.logger:
                            self.logger.debug(f"Updated state from response: turn={new_state.get('turn_number', 0)}")
                    except json.JSONDecodeError as e:
                        if self.logger:
                            self.logger.error(f"Failed to decode state from response: {str(e)}")
                        self._last_error = "State decode error"

        except httpx.TimeoutError as e:
            error_msg = "Request timed out"
            if self.logger:
                self.logger.error(f"Stream timeout: {str(e)}")
            self._last_error = "Timeout"
            yield f"Error: {error_msg}"

        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code}"
            if self.logger:
                self.logger.error(f"{error_msg}: {str(e)}")
            self._last_error = error_msg
            yield f"Error: {error_msg}"

        except httpx.RequestError as e:
            error_msg = "Failed to connect"
            if self.logger:
                self.logger.error(f"Connection error: {str(e)}")
            self._last_error = "Connection error"
            yield f"Error: {error_msg}"

        except Exception as e:
            if self.logger:
                self.logger.error(f"Unexpected error: {str(e)}")
            self._last_error = str(e)
            yield f"Error: {str(e)}"

    def get_generator(self) -> Callable:
        async def generator_wrapper(messages: list, state: Optional[Dict] = None, **kwargs):
            async for chunk in self._stream_from_endpoint(messages, state, **kwargs):
                yield chunk
        return generator_wrapper

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()