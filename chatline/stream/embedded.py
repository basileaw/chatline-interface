# stream/embedded.py

from typing import Optional, Callable, AsyncGenerator

class EmbeddedStream:
    """Handler for local embedded message streams."""
    
    def __init__(self, logger=None, generator_func=None) -> None:
        self.logger = logger
        self._last_error: Optional[str] = None
        self.generator = generator_func
        if self.logger:
            self.logger.debug("Initialized embedded stream with injected generator")

    async def _wrap_generator(
        self,
        generator_func: Callable[..., AsyncGenerator[str, None]],
        messages: list,
        state: Optional[dict] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Wrap generator with error handling and logging."""
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
            if self.logger:
                self.logger.error(f"Generator error: {e}")
            self._last_error = str(e)
            yield f"Error during generation: {e}"

    def get_generator(self) -> Callable[..., AsyncGenerator[str, None]]:
        """Return a wrapped async generator function for embedded stream processing."""
        async def generator_wrapper(
            messages: list,
            state: Optional[dict] = None,
            **kwargs
        ) -> AsyncGenerator[str, None]:
            try:
                if state and self.logger:
                    self.logger.debug(f"Processing embedded stream with state: turn={state.get('turn_number', 0)}")
                async for chunk in self._wrap_generator(self.generator, messages, state, **kwargs):
                    yield chunk
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Embedded stream error: {e}")
                self._last_error = str(e)
                yield f"Error in embedded stream: {e}"
        return generator_wrapper