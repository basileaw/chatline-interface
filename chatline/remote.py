# remote.py

import json
import aiohttp
import logging
from typing import Dict, List, AsyncGenerator, Optional, Protocol
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

class ResponseAdapter(Protocol):
    """Protocol for adapting different response formats to the expected stream format."""
    async def adapt(self, response: aiohttp.ClientResponse) -> AsyncGenerator[str, None]:
        """Convert the response stream to the expected format."""
        pass

class DefaultAdapter(ResponseAdapter):
    """Default adapter that expects the same format as generate_stream."""
    async def adapt(self, response: aiohttp.ClientResponse) -> AsyncGenerator[str, None]:
        async for line in response.content:
            if line:
                yield line.decode('utf-8')

class RemoteGenerator:
    """Handles communication with remote endpoints for chat generation."""
    
    def __init__(self, endpoint: str, adapter: Optional[ResponseAdapter] = None):
        """
        Initialize the remote generator.
        
        Args:
            endpoint (str): Full URL or path for the chat endpoint
            adapter (ResponseAdapter, optional): Response adapter for the endpoint
        """
        # If endpoint doesn't start with http, assume it's a path and prepend origin
        if not endpoint.startswith(('http://', 'https://')):
            # In production, this would be determined by the server's origin
            endpoint = urljoin('http://localhost:8000', endpoint)
            
        self.endpoint = endpoint.rstrip('/')
        self.adapter = adapter or DefaultAdapter()
        self.session: Optional[aiohttp.ClientSession] = None

    async def __call__(self, messages: List[Dict[str, str]], **kwargs) -> AsyncGenerator[str, None]:
        """
        Generate streaming responses from the remote endpoint.
        
        Args:
            messages: List of message dictionaries with role and content
            **kwargs: Additional parameters to pass to the endpoint
        """
        if not self.session:
            self.session = aiohttp.ClientSession()
            
        try:
            async with self.session.post(
                f"{self.endpoint}/chat", 
                json={"messages": messages, **kwargs}
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Endpoint error: {response.status} - {error_text}")
                    yield 'data: [ERROR]\n\n'
                    return
                    
                async for chunk in self.adapter.adapt(response):
                    yield chunk
                    
        except Exception as e:
            logger.error(f"Remote generation error: {str(e)}")
            yield 'data: [ERROR]\n\n'
            
        finally:
            if self.session and messages[-1].get('content', '').lower() in ['exit', 'quit']:
                await self.session.close()
                self.session = None