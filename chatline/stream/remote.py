# stream/remote.py

import httpx
import json
from typing import Optional, Callable, AsyncGenerator

class RemoteStream:
    """Handler for remote message streams."""
    
    def __init__(self, endpoint: str, logger=None) -> None:
        self.logger = logger
        self._last_error: Optional[str] = None
        self.endpoint = endpoint.rstrip('/')
        self.client = httpx.AsyncClient(timeout=30.0)
        if self.logger:
            self.logger.debug(f"Initialized remote stream: {self.endpoint}")

    async def _stream_from_endpoint(
        self,
        messages: list,
        state: Optional[dict] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Core method to handle streaming from remote endpoint."""
        try:
            if self.logger:
                self.logger.debug(f"Starting remote stream request with {len(messages)} messages")

            payload = {
                'messages': messages,
                'conversation_state': state
            }
            
            # Log the payload (for debugging)
            if self.logger:
                self.logger.debug(f"Sending payload to {self.endpoint}")

            async with self.client.stream('POST', self.endpoint, json=payload, timeout=30.0) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        if self.logger:
                            self.logger.debug(f"Remote response chunk: {line[:50]}...")
                        yield line

                # Process any updated state from the backend
                if response.headers.get('X-Conversation-State'):
                    try:
                        new_state = json.loads(response.headers['X-Conversation-State'])
                        if self.logger:
                            self.logger.debug(f"Received state from response: turn={new_state.get('turn_number', 0)}")
                        
                        # Store the updated state if a callback is provided
                        if 'state_callback' in kwargs and callable(kwargs['state_callback']):
                            kwargs['state_callback'](new_state)
                    except json.JSONDecodeError as e:
                        if self.logger:
                            self.logger.error(f"Failed to decode state from response: {e}")
                        self._last_error = "State decode error"

        except httpx.TimeoutError as e:
            error_msg = "Request timed out"
            if self.logger:
                self.logger.error(f"Stream timeout: {e}")
            self._last_error = "Timeout"
            yield f"Error: {error_msg}"

        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code}"
            if self.logger:
                self.logger.error(f"{error_msg}: {e}")
            self._last_error = error_msg
            yield f"Error: {error_msg}"

        except httpx.RequestError as e:
            error_msg = "Failed to connect"
            if self.logger:
                self.logger.error(f"Connection error: {e}")
            self._last_error = "Connection error"
            yield f"Error: {error_msg}"

        except Exception as e:
            if self.logger:
                self.logger.error(f"Unexpected error: {e}")
            self._last_error = str(e)
            yield f"Error: {e}"

    def get_generator(self) -> Callable[..., AsyncGenerator[str, None]]:
        """Returns a generator function for remote stream processing."""
        async def generator_wrapper(
            messages: list,
            state: Optional[dict] = None,
            **kwargs
        ) -> AsyncGenerator[str, None]:
            async for chunk in self._stream_from_endpoint(messages, state, **kwargs):
                yield chunk
        return generator_wrapper

    async def __aenter__(self) -> "RemoteStream":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit - ensures proper client cleanup."""
        if self.client:
            await self.client.aclose()