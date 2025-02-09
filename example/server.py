import os
import sys
import json
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import uvicorn

# Ensure the project root is in the Python module search path.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from chatline.generator import generate_stream

app = FastAPI()

@app.post("/chat/stream")
async def stream_chat(request: Request):
    """
    Handle chat streaming requests.
    """
    body = await request.json()
    messages = body.get('messages', [])
    conversation_state = body.get('conversation_state', {
        'messages': messages,
        'stream_type': 'remote',
        'turn': 0
    })

    generation_params = {
        'max_gen_len': body.get('max_gen_len', 1024),
        'temperature': body.get('temperature', 0.9)
    }

    conversation_state['turn'] += 1

    headers = {
        'X-Conversation-State': json.dumps(conversation_state),
        'Content-Type': 'text/event-stream'
    }

    return StreamingResponse(
        generate_stream(messages, **generation_params),
        headers=headers,
        media_type="text/event-stream"
    )

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=5000)
