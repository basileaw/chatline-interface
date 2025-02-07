# stream.py

import httpx
import json
import logging
from typing import Optional, Dict, Any

class Stream:
    def __init__(self, logger=None):
        self.logger = logger
        self.conversation_state = {
            'messages': [],
            'stream_type': None,
            'turn': 0,
            'state_version': '2.0'  # Added to track state format
        }
        self._last_error: Optional[str] = None

    def get_generator(self):
        raise NotImplementedError

    def _log_state(self, prefix: str = "") -> None:
        if self.logger:
            try:
                state_copy = {**self.conversation_state}
                # Truncate messages for logging
                if state_copy.get('messages'):
                    state_copy['messages'] = f"[{len(state_copy['messages'])} messages]"
                self.logger.debug(f"{prefix} Conversation State: {json.dumps(state_copy, indent=2)}")
            except Exception as e:
                self.logger.error(f"Error logging state: {str(e)}")

    def update_state(self, new_state: Dict[str, Any]) -> None:
        """Update stream state with new state data."""
        try:
            self.conversation_state.update({
                'messages': new_state.get('messages', self.conversation_state['messages']),
                'turn': new_state.get('turn_number', self.conversation_state['turn']),
                'last_update': new_state.get('timestamp'),
            })
            self._log_state("State updated:")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error updating state: {str(e)}")
            self._last_error = str(e)

class EmbeddedStream(Stream):
    def __init__(self, generator=None, logger=None):
        super().__init__(logger=logger)
        if not generator:
            raise ValueError("Generator function must be provided")
        self.generator = generator
        self.conversation_state['stream_type'] = 'embedded'
        if self.logger:
            self.logger.debug("Initialized embedded stream with generator")

    def get_generator(self):
        async def wrapped_generator(messages, state=None, **kwargs):
            try:
                # Update state with incoming messages and state
                self.conversation_state['messages'] = messages
                self.conversation_state['turn'] += 1

                if state:
                    self.update_state(state)

                self._log_state("Before generation:")

                # Run the actual generator and log each response chunk.
                async for chunk in self.generator(messages, **kwargs):
                    if self.logger:
                        self.logger.debug(f"Embedded response chunk: {chunk.strip()}")
                    yield chunk

                self._log_state("After generation:")

            except Exception as e:
                if self.logger:
                    self.logger.error(f"Generator error: {str(e)}")
                self._last_error = str(e)
                yield f"Error during generation: {str(e)}"

        return wrapped_generator

class RemoteStream(Stream):
    def __init__(self, endpoint, logger=None):
        super().__init__(logger=logger)
        self.endpoint = endpoint.rstrip('/')
        self.client = httpx.AsyncClient(timeout=30.0)
        self.conversation_state['stream_type'] = 'remote'
        if self.logger:
            self.logger.debug("Initialized remote stream: %s", self.endpoint)

    async def stream_from_endpoint(self, messages, state=None, **kwargs):
        try:
            # Update state with incoming messages
            self.conversation_state['messages'] = messages
            self.conversation_state['turn'] += 1

            if state:
                self.update_state(state)

            self._log_state("Before request:")

            # Prepare request payload
            payload = {
                'messages': messages,
                'conversation_state': self.conversation_state,
                **kwargs
            }

            # Stream the response from the remote endpoint
            async with self.client.stream(
                'POST',
                f"{self.endpoint}/stream",
                json=payload,
                timeout=30.0
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        if self.logger:
                            self.logger.debug(f"Remote response chunk: {line.strip()}")
                        yield line

                # After streaming completes, get final state if provided
                if response.headers.get('X-Conversation-State'):
                    try:
                        new_state = json.loads(response.headers['X-Conversation-State'])
                        self.update_state(new_state)
                        self._log_state("After response:")
                    except json.JSONDecodeError as e:
                        if self.logger:
                            self.logger.error(f"Failed to decode conversation state from response: {str(e)}")
                        self._last_error = "State decode error"

                yield 'data: [DONE]\n\n'

        except httpx.TimeoutError as e:
            if self.logger:
                self.logger.error(f"Stream timeout: {str(e)}")
            self._last_error = "Timeout"
            yield f'data: [ERROR] Request timed out\n\n'

        except httpx.HTTPStatusError as e:
            if self.logger:
                self.logger.error(f"HTTP {e.response.status_code}: {str(e)}")
            self._last_error = f"HTTP {e.response.status_code}"
            yield f'data: [ERROR] HTTP {e.response.status_code}\n\n'

        except httpx.RequestError as e:
            if self.logger:
                self.logger.error(f"Connection error: {str(e)}")
            self._last_error = "Connection error"
            yield 'data: [ERROR] Failed to connect\n\n'

        except Exception as e:
            if self.logger:
                self.logger.error(f"Unexpected error: {str(e)}")
            self._last_error = str(e)
            yield f'data: [ERROR] {str(e)}\n\n'

    def get_generator(self):
        return self.stream_from_endpoint

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()
