# generator.py

import boto3, json, time, asyncio, os
from botocore.config import Config
from botocore.exceptions import ProfileNotFound, ClientError
from typing import Any, AsyncGenerator

# Ensure EC2 metadata service is enabled
os.environ['AWS_EC2_METADATA_DISABLED'] = 'false'

MODEL_ID = "anthropic.claude-3-5-haiku-20241022-v1:0"

def _get_clients() -> tuple[Any, Any]:
    """Initialize Bedrock clients with appropriate configuration."""
    # Keep us-west-2 as Claude models are available there
    region = 'us-west-2'
    
    cfg = Config(
        region_name=region, 
        read_timeout=300, 
        connect_timeout=300,
        retries={'max_attempts': 0}
    )
    
    # Debug information to help diagnose credential issues
    print(f"Initializing Bedrock clients in region: {region}")
    print(f"AWS_EC2_METADATA_DISABLED: {os.environ.get('AWS_EC2_METADATA_DISABLED', 'Not set')}")
    
    # First try default credentials (which will use EC2 instance profile in EB)
    try:
        session = boto3.Session()
        
        # Get account ID to confirm credentials are working
        try:
            sts = session.client('sts')
            identity = sts.get_caller_identity()
            print(f"Using AWS credentials for account: {identity['Account']}")
            print(f"Identity ARN: {identity['Arn']}")
            
            # Create and return clients
            return session.client('bedrock', config=cfg), session.client('bedrock-runtime', config=cfg)
            
        except ClientError as e:
            print(f"Error with default credentials: {e}")
            raise
            
    except Exception as e:
        print(f"Failed to initialize with default credentials: {e}")
        
        # Fall back to named profile (for local development only)
        try:
            print("Attempting to use 'bedrock' profile as fallback")
            session = boto3.Session(profile_name='bedrock')
            return session.client('bedrock', config=cfg), session.client('bedrock-runtime', config=cfg)
        except ProfileNotFound:
            print("Bedrock profile not found")
            raise

# Initialize clients when module is imported
try:
    bedrock, runtime = _get_clients()
    print("Successfully initialized Bedrock clients")
except Exception as e:
    print(f"CRITICAL ERROR: Failed to initialize Bedrock clients: {e}")
    # Still define the variables to avoid NameError when functions try to use them
    bedrock, runtime = None, None

async def generate_stream(
    messages: list[dict[str, str]],
    max_gen_len: int = 1024,
    temperature: float = 0.9
) -> AsyncGenerator[str, None]:
    """Generate streaming responses from Bedrock."""
    # Using time.sleep(0) to yield control (as in the original)
    time.sleep(0)
    
    # Check if clients were successfully initialized
    if runtime is None:
        yield f"data: {{\"choices\": [{{\"delta\": {{\"content\": \"Error: Bedrock client initialization failed.\"}}}}]}}\n\n"
        yield "data: [DONE]\n\n"
        return
    
    try:
        response = runtime.converse_stream(
            modelId=MODEL_ID,
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
        print("\nRaw chunks:")
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
            if bedrock.get_foundation_model(modelIdentifier=MODEL_ID).get("modelDetails", {}).get("responseStreamingSupported"):
                asyncio.run(test_generator())
        except Exception as e:
            print(f"Test failed: {e}")