# generator.py

import boto3, json, time, asyncio
from botocore.config import Config
from botocore.exceptions import ProfileNotFound
from typing import Any, AsyncGenerator

def _get_clients() -> tuple[Any, Any]:
    """Initialize Bedrock clients with appropriate configuration."""
    cfg = Config(region_name='us-west-2', read_timeout=300, connect_timeout=300, retries={'max_attempts': 0})
    try:
        session = boto3.Session(profile_name='bedrock')
    except ProfileNotFound:
        session = boto3.Session()
    return session.client('bedrock', config=cfg), session.client('bedrock-runtime', config=cfg)

bedrock, runtime = _get_clients()
MODEL_ID = "anthropic.claude-3-5-haiku-20241022-v1:0"

async def generate_stream(
    messages: list[dict[str, str]],
    max_gen_len: int = 1024,
    temperature: float = 0.9
) -> AsyncGenerator[str, None]:
    """Generate streaming responses from Bedrock."""
    # Using time.sleep(0) to yield control (as in the original)
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
        inferenceConfig={"maxTokens": max_gen_len, "temperature": temperature}
    )
    for event in response.get('stream', []):
        text = event.get('contentBlockDelta', {}).get('delta', {}).get('text', '')
        if text:
            chunk = {"choices": [{"delta": {"content": text}}]}
            yield f"data: {json.dumps(chunk)}\n\n"
            await asyncio.sleep(0)
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

    if bedrock.get_foundation_model(modelIdentifier=MODEL_ID).get("modelDetails", {}).get("responseStreamingSupported"):
        asyncio.run(test_generator())

