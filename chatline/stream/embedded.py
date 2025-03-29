# stream/embedded.py

from typing import Optional, Callable, AsyncGenerator, Dict, Any

class EmbeddedStream:
    """Handler for local embedded message streams."""
    
    def __init__(self, logger=None, generator_func=None, aws_config: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize embedded stream with generator and configuration.
        
        Args:
            logger: Optional logger instance
            generator_func: Async generator function for message generation
            aws_config: Optional AWS configuration dictionary
        """
        self.logger = logger
        self._last_error: Optional[str] = None
        self.generator = generator_func
        self.aws_config = aws_config
        
        if self.logger:
            self.logger.debug("Initialized embedded stream with injected generator")
            if aws_config:
                # Filter out sensitive values for logging
                safe_config = {k: v for k, v in aws_config.items() 
                              if k not in ('aws_access_key_id', 'aws_secret_access_key', 'aws_session_token')}
                self.logger.debug(f"Using AWS config: {safe_config}")

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
            
            # Pass both messages and kwargs (including aws_config) to generator
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
                
                # Include aws_config in generator kwargs if available
                generator_kwargs = kwargs.copy()
                if self.aws_config:
                    generator_kwargs['aws_config'] = self.aws_config
                # Pass the logger to the generator
                generator_kwargs['logger'] = self.logger
                
                async for chunk in self._wrap_generator(
                    self.generator, 
                    messages, 
                    state, 
                    **generator_kwargs
                ):
                    yield chunk
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Embedded stream error: {e}")
                self._last_error = str(e)
                yield f"Error in embedded stream: {e}"
        return generator_wrapper