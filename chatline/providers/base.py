# providers/base.py

from abc import ABC, abstractmethod
from typing import Dict, Any, AsyncGenerator, Optional

class BaseProvider(ABC):
    """
    Base class for all providers.
    
    Providers are responsible for generating responses from different LLM services.
    Each provider must implement the generate_stream method that yields response chunks.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, logger=None):
        """
        Initialize the provider with configuration.
        
        Args:
            config: Provider-specific configuration dictionary
            logger: Optional logger instance
        """
        self.config = config or {}
        self.logger = logger
    
    def _log_debug(self, msg: str) -> None:
        """Helper method for debug logging."""
        if self.logger:
            self.logger.debug(msg)
    
    def _log_error(self, msg: str) -> None:
        """Helper method for error logging."""
        if self.logger:
            self.logger.error(msg)
    
    @abstractmethod
    async def generate_stream(
        self,
        messages: list,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        Generate a streaming response from the provider.
        
        Args:
            messages: List of conversation messages
            **kwargs: Additional provider-specific parameters
            
        Yields:
            Chunks of the generated response in the common format:
            data: {"choices": [{"delta": {"content": "chunk text"}}]}\n\n
            
        Note:
            The final chunk should be:
            data: [DONE]\n\n
        """
        pass
    
    def format_error_chunk(self, error_message: str) -> str:
        """
        Format an error message as a response chunk.
        
        Args:
            error_message: Error message to format
            
        Returns:
            Formatted error message as a response chunk
        """
        import json
        error_chunk = {"choices": [{"delta": {"content": f"Error: {error_message}"}}]}
        return f"data: {json.dumps(error_chunk)}\n\n"