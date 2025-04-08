# providers/bedrock.py

import boto3, json, time, asyncio, os
from botocore.config import Config
from botocore.exceptions import ProfileNotFound, ClientError
from typing import Any, AsyncGenerator, Dict, Optional, Tuple

from .base import BaseProvider
from . import register_provider

# Default model ID
DEFAULT_MODEL_ID = "anthropic.claude-3-5-haiku-20241022-v1:0"

# Client cache dictionary
_CLIENT_CACHE = {}

class BedrockProvider(BaseProvider):
    """Provider for AWS Bedrock LLM services."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, logger=None):
        """
        Initialize the Bedrock provider.
        
        Args:
            config: Bedrock-specific configuration with keys like:
                - region: AWS region for Bedrock
                - profile_name: AWS profile to use
                - model_id: Bedrock model ID
                - timeout: Request timeout in seconds
            logger: Optional logger instance
        """
        super().__init__(config, logger)
        
        # Initialize to None, will be created on first use
        self.bedrock_client = None
        self.runtime_client = None
        self.model_id = DEFAULT_MODEL_ID
    
    def get_bedrock_clients(self) -> Tuple[Any, Any, str]:
        """
        Get or create Bedrock clients.
        
        Returns:
            tuple: (bedrock_client, bedrock_runtime_client, model_id)
        """
        config = self.config
        
        # Use a cache key based on the config
        cache_key = None
        if config:
            # Create a cache key from the most important config values that would affect client behavior
            key_elements = [
                config.get('region'),
                config.get('profile_name'),
                config.get('endpoint_url'),
                config.get('aws_access_key_id', '')[:4],  # Just use first few chars for security
                str(config.get('timeout'))
            ]
            cache_key = ":".join(str(k) for k in key_elements if k)
            
            # Check if we already have clients for this config
            if cache_key in _CLIENT_CACHE:
                self._log_debug(f"Using cached Bedrock clients for config: {cache_key}")
                return _CLIENT_CACHE[cache_key]
        
        # Ensure EC2 metadata service is enabled
        os.environ['AWS_EC2_METADATA_DISABLED'] = 'false'
        
        # Region resolution with priority order
        region = config.get('region') or os.environ.get('AWS_BEDROCK_REGION') or os.environ.get('AWS_REGION') or os.environ.get('AWS_DEFAULT_REGION', 'us-west-2')
        
        # Get the model ID (default is Claude 3.5 Haiku)
        model_id = config.get('model_id') or os.environ.get('AWS_BEDROCK_MODEL_ID', DEFAULT_MODEL_ID)
        
        # Build boto3 config with potential overrides
        boto_config = Config(
            region_name=region,
            retries={'max_attempts': config.get('max_retries', 2)},
            read_timeout=config.get('timeout', 300),
            connect_timeout=config.get('timeout', 300)
        )
        
        self._log_debug(f"Initializing Bedrock clients in region: {region}")
        self._log_debug(f"Using model: {model_id}")
        
        # Session parameters (only if explicitly provided)
        session_params = {}
        if config.get('profile_name'):
            session_params['profile_name'] = config['profile_name']
        if config.get('aws_access_key_id') and config.get('aws_secret_access_key'):
            session_params['aws_access_key_id'] = config['aws_access_key_id']
            session_params['aws_secret_access_key'] = config['aws_secret_access_key']
            if config.get('aws_session_token'):
                session_params['aws_session_token'] = config['aws_session_token']
        
        # Client parameters
        client_params = {'config': boto_config}
        if config.get('endpoint_url'):
            client_params['endpoint_url'] = config['endpoint_url']
        
        try:
            # Create session with optional parameters - uses default credential chain
            session = boto3.Session(**session_params)
            
            # Create and verify clients
            bedrock = session.client('bedrock', **client_params)
            runtime = session.client('bedrock-runtime', **client_params)
            
            # Verify credentials by making a basic call
            try:
                sts = session.client('sts')
                identity = sts.get_caller_identity()
                self._log_debug(f"Using credentials for account: {identity['Account']}")
            except Exception as e:
                self._log_debug(f"Warning: Could not verify credentials: {e}")
            
            # Store in cache if we have a cache key
            if cache_key:
                _CLIENT_CACHE[cache_key] = (bedrock, runtime, model_id)
                
            return bedrock, runtime, model_id
        
        except Exception as e:
            self._log_error(f"Critical error initializing Bedrock clients: {e}")
            return None, None, model_id
    
    async def generate_stream(
        self,
        messages: list,
        max_gen_len: int = 1024,
        temperature: float = 0.9,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        Generate streaming responses from AWS Bedrock.
        
        Args:
            messages: List of conversation messages
            max_gen_len: Maximum tokens to generate
            temperature: Temperature for generation
            **kwargs: Additional keyword arguments (unused)
            
        Yields:
            Chunks of the generated response
        """
        # Using time.sleep(0) to yield control (as in the original)
        time.sleep(0)
        
        # Initialize clients if not already done
        if not self.bedrock_client or not self.runtime_client:
            self.bedrock_client, self.runtime_client, self.model_id = self.get_bedrock_clients()
        
        # Check if clients were successfully initialized
        if self.bedrock_client is None or self.runtime_client is None:
            yield self.format_error_chunk("Bedrock client initialization failed.")
            yield "data: [DONE]\n\n"
            return
        
        try:
            response = self.runtime_client.converse_stream(
                modelId=self.model_id,
                messages=[
                    {"role": m["role"], "content": [{"text": m["content"]}]}
                    for m in messages if m["role"] != "system"
                ],
                system=[
                    {"text": m["content"]}
                    for m in messages if m["role"] == "system"
                ],
                inferenceConfig={"maxTokens": max_gen_len, "temperature": temperature}
            )
            for event in response.get('stream', []):
                text = event.get('contentBlockDelta', {}).get('delta', {}).get('text', '')
                if text:
                    chunk = {"choices": [{"delta": {"content": text}}]}
                    yield f"data: {json.dumps(chunk)}\n\n"
                    await asyncio.sleep(0)
            yield "data: [DONE]\n\n"
        except Exception as e:
            self._log_error(f"Error during generation: {str(e)}")
            yield self.format_error_chunk(str(e))
            yield "data: [DONE]\n\n"

def register():
    """Register this provider with the registry."""
    register_provider("bedrock", BedrockProvider)