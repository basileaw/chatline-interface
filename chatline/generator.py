# generator.py

import asyncio
from typing import Any, AsyncGenerator, Dict, Optional, List

from .providers import generate_with_provider

# Keep the original Bedrock provider as the default for backward compatibility
DEFAULT_PROVIDER = "bedrock"

async def generate_stream(
    messages: List[Dict[str, str]],
    max_gen_len: int = 1024,
    temperature: float = 0.7,
    provider: str = DEFAULT_PROVIDER,
    provider_config: Optional[Dict[str, Any]] = None,
    aws_config: Optional[Dict[str, Any]] = None,
    logger=None,
    **kwargs
) -> AsyncGenerator[str, None]:
    """
    Generate streaming responses from the specified provider.
    
    This function maintains backward compatibility with the original API
    while adding support for multiple providers.
    
    Args:
        messages: List of conversation messages
        max_gen_len: Maximum tokens to generate
        temperature: Temperature for generation
        provider: Provider name (e.g., 'bedrock', 'openrouter')
        provider_config: Provider-specific configuration
        aws_config: (Legacy) AWS configuration for Bedrock
        logger: Optional logger instance
        **kwargs: Additional provider-specific parameters
        
    Yields:
        Chunks of the generated response
    """
    # For backward compatibility, if aws_config is provided but no provider_config,
    # use aws_config as the provider_config for Bedrock
    if provider == "bedrock" and aws_config and not provider_config:
        provider_config = aws_config
    
    # Prepare the config object
    config = provider_config or {}
    
    # Debug logging
    if logger:
        logger.debug(f"Using provider: {provider}")
        # Don't log sensitive information like API keys
        safe_config = {k: v for k, v in config.items() 
                      if k not in ('api_key', 'aws_access_key_id', 'aws_secret_access_key')}
        if safe_config:
            logger.debug(f"Provider config: {safe_config}")
    
    # Call the provider to generate the response
    async for chunk in generate_with_provider(
        provider_name=provider,
        messages=messages,
        provider_config=config,
        max_gen_len=max_gen_len,
        temperature=temperature,
        logger=logger,
        **kwargs
    ):
        yield chunk

if __name__ == "__main__":
    # For the test script, we can use print statements directly
    import logging
    
    # Setup basic logger for testing
    test_logger = logging.getLogger("provider_test")
    test_logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
    test_logger.addHandler(handler)
    
    async def test_default_provider() -> None:
        """Test the default Bedrock provider."""
        messages = [
            {"role": "user", "content": "Tell me a joke about computers."},
            {"role": "system", "content": "Be helpful and humorous."}
        ]
        print("\nTesting with default provider (Bedrock):")
        try:
            async for chunk in generate_stream(messages, logger=test_logger):
                print(f"\nChunk: {chunk}")
                try:
                    if chunk.startswith("data: "):
                        data = chunk.replace("data: ", "").strip()
                        if data != "[DONE]":
                            import json
                            content = json.loads(data)["choices"][0]["delta"]["content"]
                            print("Parsed content:", content, end="", flush=True)
                except:
                    continue
        except Exception as e:
            print(f"Test failed: {e}")
    
    async def test_openrouter_provider() -> None:
        """Test the OpenRouter provider, if API key is available."""
        import os
        
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            print("\nSkipping OpenRouter test (no API key found)")
            return
            
        messages = [
            {"role": "user", "content": "Tell me a joke about computers."},
            {"role": "system", "content": "Be helpful and humorous."}
        ]
        
        config = {
            "api_key": api_key,
            "model": "anthropic/claude-3-haiku-20240307"
        }
        
        print("\nTesting with OpenRouter provider:")
        try:
            async for chunk in generate_stream(
                messages, 
                provider="openrouter",
                provider_config=config,
                logger=test_logger
            ):
                print(f"\nChunk: {chunk}")
                try:
                    if chunk.startswith("data: "):
                        data = chunk.replace("data: ", "").strip()
                        if data != "[DONE]":
                            import json
                            content = json.loads(data)["choices"][0]["delta"]["content"]
                            print("Parsed content:", content, end="", flush=True)
                except:
                    continue
        except Exception as e:
            print(f"Test failed: {e}")
    
    # Run the tests
    async def run_tests():
        await test_default_provider()
        await test_openrouter_provider()
        
    # Only run tests if executed directly
    try:
        asyncio.run(run_tests())
    except Exception as e:
        print(f"Tests failed: {e}")