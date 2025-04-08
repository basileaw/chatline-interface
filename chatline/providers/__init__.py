# providers/__init__.py

from typing import Dict, Any, Callable, AsyncGenerator, Optional, Type
import importlib

# Type hint for provider class
ProviderType = Type["BaseProvider"]

# Registry to store provider classes
_PROVIDER_REGISTRY = {}

def register_provider(name: str, provider_class: ProviderType) -> None:
    """
    Register a provider class with a given name.
    
    Args:
        name: Provider identifier (e.g., 'bedrock', 'openrouter')
        provider_class: Provider class that implements the BaseProvider interface
    """
    _PROVIDER_REGISTRY[name.lower()] = provider_class

def get_provider(
    provider_name: str = "bedrock",
    provider_config: Optional[Dict[str, Any]] = None,
    logger=None
) -> Any:
    """
    Get an instance of the specified provider.
    
    Args:
        provider_name: Provider identifier (defaults to 'bedrock')
        provider_config: Provider-specific configuration dictionary
        logger: Optional logger instance
        
    Returns:
        An initialized provider instance
        
    Raises:
        ValueError: If the provider name is not recognized
    """
    # Ensure provider_config is not None
    provider_config = provider_config or {}
    
    # Debug logging
    if logger:
        logger.debug(f"Getting provider: {provider_name}")
    
    # Try to get the provider class from the registry
    provider_name = provider_name.lower()
    
    # Lazy load the provider if not already registered
    if provider_name not in _PROVIDER_REGISTRY:
        try:
            # Import the module dynamically
            module_name = f"chatline.providers.{provider_name}"
            module = importlib.import_module(module_name)
            
            # Auto-registration should happen in the imported module
            if provider_name not in _PROVIDER_REGISTRY and hasattr(module, 'register'):
                module.register()
                
        except ImportError:
            if logger:
                logger.error(f"Provider module not found: {provider_name}")
            raise ValueError(f"Unknown provider: {provider_name}")
    
    # Get the provider class from the registry
    if provider_name not in _PROVIDER_REGISTRY:
        if logger:
            logger.error(f"Provider not registered: {provider_name}")
        raise ValueError(f"Provider not registered: {provider_name}")
    
    provider_class = _PROVIDER_REGISTRY[provider_name]
    
    # Instantiate and return the provider
    return provider_class(provider_config, logger)

async def generate_with_provider(
    provider_name: str,
    messages: list,
    provider_config: Optional[Dict[str, Any]] = None,
    **kwargs
) -> AsyncGenerator[str, None]:
    """
    Generate a response using the specified provider.
    
    Args:
        provider_name: Provider identifier
        messages: List of conversation messages
        provider_config: Provider-specific configuration
        **kwargs: Additional keyword arguments to pass to the provider
        
    Yields:
        Chunks of the generated response
    """
    provider = get_provider(provider_name, provider_config, kwargs.get("logger"))
    async for chunk in provider.generate_stream(messages, **kwargs):
        yield chunk

# Import BaseProvider here to avoid circular imports
from .base import BaseProvider

# Default exports
__all__ = ['register_provider', 'get_provider', 'generate_with_provider', 'BaseProvider']