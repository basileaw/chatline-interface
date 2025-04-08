# providers/openrouter.py

import json
import time
import asyncio
import os
import httpx
from typing import Any, AsyncGenerator, Dict, Optional, List

from .base import BaseProvider
from . import register_provider

class OpenRouterProvider(BaseProvider):
    """Provider for OpenRouter LLM services."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, logger=None):
        """
        Initialize the OpenRouter provider.
        
        Args:
            config: OpenRouter-specific configuration with keys like:
                - api_key: OpenRouter API key (overrides environment variable)
                - model: Model identifier (optional)
                - referer: HTTP-Referer for OpenRouter tracking
                - title: X-Title for OpenRouter tracking
            logger: Optional logger instance
        """
        super().__init__(config, logger)
        
        # Extract API key with priority: config > environment variable
        self.api_key = self.config.get('api_key') or os.environ.get('OPENROUTER_API_KEY')
        if not self.api_key:
            self._log_error("OpenRouter API key not found. Set OPENROUTER_API_KEY environment variable or pass api_key in provider_config.")
            raise ValueError("OpenRouter API key required")
        
        # Extract configuration options
        self.model = self.config.get('model') or os.environ.get('OPENROUTER_MODEL_ID')
        self.referer = self.config.get('referer', 'https://github.com/anotherbazeinthewall/chatline-interface/')
        self.title = self.config.get('title', 'ChatLine Interface')
        self.timeout = self.config.get('timeout', 60.0)
        
        # Log initialization status
        if self.model:
            self._log_debug(f"Using OpenRouter with specified model: {self.model}")
        else:
            self._log_debug("Using OpenRouter with default model configured for this API key")
    
    async def generate_stream(
        self,
        messages: List[Dict[str, str]],
        max_gen_len: int = 1024,
        temperature: float = 0.7,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        Generate streaming responses from OpenRouter.
        
        Args:
            messages: List of conversation messages
            max_gen_len: Maximum tokens to generate
            temperature: Temperature for generation
            **kwargs: Additional parameters
            
        Yields:
            Chunks of the generated response
        """
        # Using time.sleep(0) to yield control
        time.sleep(0)
        
        # Set up headers
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # Add tracking headers if provided
        if self.referer:
            headers["HTTP-Referer"] = self.referer
        if self.title:
            headers["X-Title"] = self.title
        
        # Prepare request payload
        request_data = {
            "messages": messages,
            "stream": True,
            "max_tokens": max_gen_len,
            "temperature": temperature
        }
        
        # Only add model if explicitly specified
        if self.model:
            request_data["model"] = self.model
        
        # Add additional parameters if provided
        for param in ['top_p', 'presence_penalty', 'frequency_penalty']:
            if param in kwargs:
                request_data[param] = kwargs[param]
            elif param in self.config:
                request_data[param] = self.config[param]
        
        self._log_debug(f"Making request to OpenRouter API")
        self._log_debug(f"Request data: {json.dumps({k: v for k, v in request_data.items() if k != 'messages'})}")
        
        try:
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST",
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json=request_data,
                    timeout=self.timeout
                ) as response:
                    # Handle error responses
                    if response.status_code != 200:
                        error_text = await response.aread()
                        try:
                            error_text = error_text.decode('utf-8')
                        except:
                            error_text = str(error_text)
                        self._log_error(f"OpenRouter API error: {response.status_code} - {error_text}")
                        error_chunk = {"choices": [{"delta": {"content": f"Error: HTTP {response.status_code} - {error_text}"}}]}
                        yield f"data: {json.dumps(error_chunk)}\n\n"
                        yield "data: [DONE]\n\n"
                        return
                    
                    # Process the streaming response
                    async for line in response.aiter_lines():
                        line = line.strip()
                        if not line:
                            continue
                            
                        # OpenRouter uses the same SSE format as OpenAI
                        if line.startswith('data: '):
                            data_str = line[6:]  # Remove 'data: ' prefix
                            
                            # Just pass through [DONE] marker
                            if data_str == '[DONE]':
                                yield "data: [DONE]\n\n"
                                break
                                
                            try:
                                data = json.loads(data_str)
                                if 'choices' in data and len(data['choices']) > 0:
                                    # Extract the content from the delta
                                    delta = data['choices'][0].get('delta', {})
                                    content = delta.get('content')
                                    
                                    if content:
                                        # Handle first chunk leading whitespace issue
                                        if not hasattr(self, '_first_chunk_sent'):
                                            self._first_chunk_sent = True
                                            content = content.lstrip()
                                        
                                        # Format it to match the expected output format
                                        chunk = {"choices": [{"delta": {"content": content}}]}
                                        yield f"data: {json.dumps(chunk)}\n\n"
                                        await asyncio.sleep(0)
                            except json.JSONDecodeError as e:
                                self._log_error(f"Error decoding JSON from OpenRouter stream: {e}, line: {line}")
                                continue
                    
                    # Ensure final [DONE] is sent if not already sent
                    if not line.endswith('[DONE]'):
                        yield "data: [DONE]\n\n"
                        
        except Exception as e:
            self._log_error(f"Error during OpenRouter request: {str(e)}")
            error_chunk = {"choices": [{"delta": {"content": f"Error: {str(e)}"}}]}
            yield f"data: {json.dumps(error_chunk)}\n\n"
            yield "data: [DONE]\n\n"

def register():
    """Register this provider with the registry."""
    register_provider("openrouter", OpenRouterProvider)