# embedded.py

from typing import Optional, Dict, Any, AsyncGenerator, Callable
from .generator import generate_stream

class EmbeddedStream:
    """Handler for local embedded message streams."""
    
    def __init__(self, logger=None):
        self.logger = logger
        self._last_error: Optional[str] = None
        self.generator = generate_stream
        if self.logger:
            self.logger.debug("Initialized embedded stream with default generator")

    async def _wrap_generator(self, generator_func: Callable, messages: list, state: Optional[Dict] = None, **kwargs) -> AsyncGenerator[str, None]:
        """Helper method to wrap generator with error handling and logging.
        
        Args:
            generator_func: The core generation function to wrap
            messages: List of messages to process
            state: Optional conversation state
            **kwargs: Additional arguments passed to the generator
            
        Yields:
            str: Generated message chunks
        """
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
        """Returns a wrapped generator function for embedded stream processing.
        
        Returns:
            Callable: Async generator function that yields message chunks
        """
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