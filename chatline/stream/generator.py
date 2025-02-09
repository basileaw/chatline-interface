# generator.py

import boto3
import json
import time
import asyncio
from botocore.config import Config
from botocore.exceptions import ProfileNotFound

def _get_clients():
    """Initialize Bedrock clients with appropriate configuration."""
    runtime_config = Config(
        region_name='us-west-2',  # Always use us-west-2 for Bedrock
        read_timeout=300,
        connect_timeout=300,
        retries={'max_attempts': 0}
    )
    
    try:
        # Try to use the bedrock profile first
        session = boto3.Session(profile_name='bedrock')
    except ProfileNotFound:
        # Fall back to default credentials (IAM role or default profile)
        session = boto3.Session()
        
    return (
        session.client('bedrock', config=runtime_config),
        session.client('bedrock-runtime', config=runtime_config)
    )

bedrock, runtime = _get_clients()
MODEL_ID = "anthropic.claude-3-5-haiku-20241022-v1:0"

async def generate_stream(messages, max_gen_len=1024, temperature=0.9):
    """Generate streaming responses from Bedrock."""
    # Preserved from original; note that in async code, you might prefer asyncio.sleep(0)
    time.sleep(0)
    
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
        inferenceConfig={
            "maxTokens": max_gen_len,
            "temperature": temperature
        }
    )
    
    for event in response.get('stream', []):
        text = event.get('contentBlockDelta', {}).get('delta', {}).get('text', '')
        if text:
            chunk = {
                "choices": [{
                    "delta": {"content": text}
                }]
            }
            yield f'data: {json.dumps(chunk)}\n\n'
            await asyncio.sleep(0)
    
    yield 'data: [DONE]\n\n'

if __name__ == "__main__":
    async def test_generator():
        messages = [
            {"role": "user", "content": "Tell me a joke about computers."},
            {"role": "system", "content": "Be helpful and humorous."}
        ]
        
        print("\nRaw chunks:")
        async for chunk in generate_stream(messages):
            print(f"\nChunk: {chunk}")
            try:
                if chunk.startswith('data: '):
                    data = json.loads(chunk.replace('data: ', '').strip())
                    if data != '[DONE]':
                        print("Parsed content:", data['choices'][0]['delta']['content'], end='', flush=True)
            except json.JSONDecodeError:
                continue

    # Run test if streaming is supported
    if bedrock.get_foundation_model(modelIdentifier=MODEL_ID)\
            .get('modelDetails', {})\
            .get('responseStreamingSupported'):
        asyncio.run(test_generator())
