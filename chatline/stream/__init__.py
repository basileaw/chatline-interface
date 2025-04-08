# stream/__init__.py

from typing import Optional, Callable, Dict, Any
from .embedded import EmbeddedStream
from .remote import RemoteStream

class Stream:
    """Base class for handling message streaming."""
    
    def __init__(self, logger=None):
        self.logger = logger
        self._last_error: Optional[str] = None

    @classmethod 
    def create(cls, endpoint: Optional[str] = None, logger=None, 
               generator_func=None, aws_config: Optional[Dict[str, Any]] = None,
               provider: str = "openrouter", provider_config: Optional[Dict[str, Any]] = None) -> 'Stream':
        """
        Create appropriate stream handler based on endpoint presence.
        
        Args:
            endpoint: Remote endpoint URL or None for embedded mode
            logger: Optional logger instance
            generator_func: Generator function for embedded mode
            aws_config: (Legacy) AWS configuration for embedded mode
            provider: Provider name for embedded mode
            provider_config: Provider-specific configuration
            
        Returns:
            Stream instance (either RemoteStream or EmbeddedStream)
        """
        if endpoint:
            return RemoteStream(endpoint, logger=logger)
            
        # For backward compatibility: if aws_config is provided but provider_config is not,
        # and the provider is 'bedrock', use aws_config as the provider_config
        if provider == "bedrock" and aws_config and not provider_config:
            provider_config = aws_config
            
        return EmbeddedStream(
            logger=logger, 
            generator_func=generator_func, 
            provider=provider,
            provider_config=provider_config
        )

    def get_generator(self) -> Callable:
        """Return a generator function for message streaming."""
        raise NotImplementedError

__all__ = ['Stream']