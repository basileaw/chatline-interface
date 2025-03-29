# generator.py

import boto3, json, time, asyncio, os
from botocore.config import Config
from botocore.exceptions import ProfileNotFound, ClientError
from typing import Any, AsyncGenerator, Dict, Optional

# Default model ID
DEFAULT_MODEL_ID = "anthropic.claude-3-5-haiku-20241022-v1:0"

def get_bedrock_clients(config: Optional[Dict[str, Any]] = None) -> tuple[Any, Any]:
    """
    Get Bedrock clients with flexible configuration options.
    
    Args:
        config (dict, optional): Override configuration with any of these keys:
            - region: AWS region for Bedrock (overrides environment variables)
            - profile_name: AWS profile to use (for local development)
            - timeout: Request timeout in seconds
            - max_retries: Maximum retry attempts
            - endpoint_url: Custom endpoint URL (for testing/VPC endpoints)
            - model_id: Bedrock model ID to use
            - aws_access_key_id: Explicit access key (not recommended)
            - aws_secret_access_key: Explicit secret key (not recommended)
    
    Returns:
        tuple: (bedrock_client, bedrock_runtime_client, model_id)
    """
    # Initialize with empty dict if None
    config = config or {}
    
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
    
    print(f"Initializing Bedrock clients in region: {region}")
    print(f"Using model: {model_id}")
    
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
            print(f"Using credentials for account: {identity['Account']}")
        except Exception as e:
            print(f"Warning: Could not verify credentials: {e}")
        
        return bedrock, runtime, model_id
    
    except Exception as e:
        print(f"Critical error initializing Bedrock clients: {e}")
        return None, None, model_id

# Initialize clients when module is imported (with default settings)
bedrock, runtime, MODEL_ID = get_bedrock_clients()

async def generate_stream(
    messages: list[dict[str, str]],
    max_gen_len: int = 1024,
    temperature: float = 0.9,
    aws_config: Optional[Dict[str, Any]] = None
) -> AsyncGenerator[str, None]:
    """
    Generate streaming responses from Bedrock.
    
    Args:
        messages: List of conversation messages
        max_gen_len: Maximum tokens to generate
        temperature: Temperature for generation
        aws_config: Optional AWS configuration overrides
    """
    # Using time.sleep(0) to yield control (as in the original)
    time.sleep(0)
    
    # Use provided config to get clients if specified
    current_bedrock, current_runtime, model_id = (bedrock, runtime, MODEL_ID)
    if aws_config:
        try:
            b, r, m = get_bedrock_clients(aws_config)
            if b and r:
                current_bedrock, current_runtime, model_id = b, r, m
        except Exception as e:
            print(f"Error using custom AWS config: {e}")
    
    # Check if clients were successfully initialized
    if current_runtime is None:
        yield f"data: {{\"choices\": [{{\"delta\": {{\"content\": \"Error: Bedrock client initialization failed.\"}}}}]}}\n\n"
        yield "data: [DONE]\n\n"
        return
    
    try:
        response = current_runtime.converse_stream(
            modelId=model_id,
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
        print(f"Error during generation: {str(e)}")
        error_message = str(e)
        # Format error as a valid response chunk
        error_chunk = {"choices": [{"delta": {"content": f"Error: {error_message}"}}]}
        yield f"data: {json.dumps(error_chunk)}\n\n"
        yield "data: [DONE]\n\n"

if __name__ == "__main__":
    async def test_generator() -> None:
        messages = [
            {"role": "user", "content": "Tell me a joke about computers."},
            {"role": "system", "content": "Be helpful and humorous."}
        ]
        print("\nTesting with default configuration:")
        async for chunk in generate_stream(messages):
            print(f"\nChunk: {chunk}")
            try:
                if chunk.startswith("data: "):
                    data = json.loads(chunk.replace("data: ", "").strip())
                    if data != "[DONE]":
                        print("Parsed content:", data["choices"][0]["delta"]["content"], end="", flush=True)
            except json.JSONDecodeError:
                continue

    # Only run test if Bedrock client is available
    if bedrock is not None:
        try:
            asyncio.run(test_generator())
        except Exception as e:
            print(f"Test failed: {e}")