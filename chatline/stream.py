# stream.py

import httpx
import json
import logging

class Stream:
    def __init__(self, logger=None):
        self.logger = logger
        self.conversation_state = {
            'messages': [],
            'stream_type': None,
            'turn': 0
        }

    def get_generator(self):
        raise NotImplementedError

    def _log_state(self, prefix=""):
        if self.logger:
            self.logger.debug(f"{prefix} Conversation State: {json.dumps(self.conversation_state, indent=2)}")

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
        async def wrapped_generator(messages, **kwargs):
            # Update state with incoming messages
            self.conversation_state['messages'] = messages
            self.conversation_state['turn'] += 1
            self._log_state("Before generation:")

            # Run the actual generator
            async for chunk in self.generator(messages, **kwargs):
                yield chunk

            self._log_state("After generation:")

        return wrapped_generator

class RemoteStream(Stream):
    def __init__(self, endpoint, logger=None):
        super().__init__(logger=logger)
        self.endpoint = endpoint.rstrip('/')
        self.client = httpx.AsyncClient(timeout=30.0)
        self.conversation_state['stream_type'] = 'remote'
        if self.logger:
            self.logger.debug("Initialized remote stream: %s", self.endpoint)

    async def stream_from_endpoint(self, messages, **kwargs):
        try:
            # Update state with incoming messages
            self.conversation_state['messages'] = messages
            self.conversation_state['turn'] += 1
            self._log_state("Before request:")

            # Stream the response
            async with self.client.stream(
                'POST',
                f"{self.endpoint}/stream",
                json={'messages': messages, 'conversation_state': self.conversation_state, **kwargs},
                timeout=30.0
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        yield line

                # After streaming completes, get final state if provided
                if response.headers.get('X-Conversation-State'):
                    try:
                        self.conversation_state = json.loads(
                            response.headers['X-Conversation-State']
                        )
                        self._log_state("After response:")
                    except json.JSONDecodeError:
                        if self.logger:
                            self.logger.error("Failed to decode conversation state from response")

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