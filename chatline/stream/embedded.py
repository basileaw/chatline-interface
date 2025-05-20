# stream/embedded.py

from typing import Optional, Callable, AsyncGenerator, Dict, Any

class EmbeddedStream:
    """Handler for local embedded message streams."""
    
    def __init__(self, logger=None, generator_func=None, 
                 provider: str = "bedrock", 
                 provider_config: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize embedded stream with generator and configuration.
        
        Args:
            logger: Optional logger instance
            generator_func: Async generator function for message generation
            provider: Provider name to use
            provider_config: Provider-specific configuration dictionary
        """
        self.logger = logger
        self._last_error: Optional[str] = None
        self.generator = generator_func
        self.provider = provider
        self.provider_config = provider_config or {}
        
        if self.logger:
            self.logger.debug(f"Initialized embedded stream with provider: {provider}")
            # Filter out sensitive values for logging
            safe_config = {k: v for k, v in self.provider_config.items() 
                          if k not in ('api_key', 'aws_access_key_id', 'aws_secret_access_key', 'aws_session_token')}
            if safe_config:
                self.logger.debug(f"Provider config: {safe_config}")

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
            
            # Pass messages, provider, provider_config, and additional kwargs to generator
            generator_kwargs = {
                "provider": self.provider,
                "provider_config": self.provider_config,
                "logger": self.logger,
                **kwargs
            }
            
            async for chunk in generator_func(messages, **generator_kwargs):
                if self.logger:
                    self.logger.debug(f"Generated chunk: {chunk.rstrip()}")
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
                
                async for chunk in self._wrap_generator(
                    self.generator, 
                    messages, 
                    state, 
                    **kwargs
                ):
                    yield chunk
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Embedded stream error: {e}")
                self._last_error = str(e)
                yield f"Error in embedded stream: {e}"
        return generator_wrapper