# remote.py 

import httpx
import json
from typing import Optional, Dict, Any, AsyncGenerator, Callable

class RemoteStream:
    """Handler for remote message streams."""
    
    def __init__(self, endpoint: str, logger=None):
        self.logger = logger
        self._last_error: Optional[str] = None
        self.endpoint = endpoint.rstrip('/')
        self.client = httpx.AsyncClient(timeout=30.0)
        if self.logger:
            self.logger.debug(f"Initialized remote stream: {self.endpoint}")

    async def _stream_from_endpoint(self, messages: list, state: Optional[Dict] = None, **kwargs) -> AsyncGenerator[str, None]:
        """Core method to handle streaming from remote endpoint.
        
        Args:
            messages: List of messages to process
            state: Optional conversation state
            **kwargs: Additional arguments passed to the remote endpoint
            
        Yields:
            str: Message chunks from remote endpoint or error messages
        """
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
        """Returns a generator function for remote stream processing.
        
        Returns:
            Callable: Async generator function that yields message chunks from remote endpoint
        """
        async def generator_wrapper(messages: list, state: Optional[Dict] = None, **kwargs):
            async for chunk in self._stream_from_endpoint(messages, state, **kwargs):
                yield chunk
        return generator_wrapper

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - ensures proper client cleanup."""
        if self.client:
            await self.client.aclose()