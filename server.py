# server.py

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import json
import uvicorn
from chatline.generator import generate_stream

app = FastAPI()

@app.post("/chat/stream")
async def stream_chat(request: Request):
    """
    Chat streaming endpoint that handles both message generation and conversation state.
    All processing logic is contained within this route for easy portability.
    
    Expected request body:
    {
        "messages": [...],
        "conversation_state": {
            "messages": [...],
            "stream_type": "remote",
            "turn": 0,
            ...any additional keys...
        },
        "max_gen_len": 1024,  # optional
        "temperature": 0.9    # optional
    }
    """
    # Get and process request body
    body = await request.json()
    
    # Extract core parameters
    messages = body.get('messages', [])
    conversation_state = body.get('conversation_state', {
        'messages': messages,
        'stream_type': 'remote',
        'turn': 0
    })
    
    # Extract optional generation parameters
    generation_params = {
        'max_gen_len': body.get('max_gen_len', 1024),
        'temperature': body.get('temperature', 0.9)
    }
    
    # Update conversation state
    conversation_state['turn'] += 1
    
    # You can add any additional state processing here
    # conversation_state['your_key'] = your_value
    
    # Create response headers with updated state
    headers = {
        'X-Conversation-State': json.dumps(conversation_state),
        'Content-Type': 'text/event-stream'
    }
    
    # Return streaming response
    return StreamingResponse(
        generate_stream(messages, **generation_params),
        headers=headers,
        media_type="text/event-stream"
    )

if __name__ == "__main__":
    uvicorn.run("server:app", host="127.0.0.1", port=5000, reload=True)