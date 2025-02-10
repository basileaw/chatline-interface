# server.py

import json
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from chatline.stream.generator import generate_stream

app = FastAPI()

@app.post("/chat")
async def stream_chat(request: Request):
    # Parse the request body and handle potential None cases
    body = await request.json()
    messages = body.get('messages', [])
    
    # Get the state from the request, defaulting to an empty state if not present
    state = {
        'messages': messages,
        'stream_type': 'remote',
        'turn_number': 0
    }
    
    # If we received state information, update our default state
    if 'conversation_state' in body and body['conversation_state']:
        received_state = body['conversation_state']
        state['turn_number'] = received_state.get('turn_number', 0)
    
    # Increment the turn number
    state['turn_number'] += 1

    headers = {
        'Content-Type': 'text/event-stream',
        'X-Conversation-State': json.dumps(state)
    }

    return StreamingResponse(
        generate_stream(messages),
        headers=headers,
        media_type="text/event-stream"
    )

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)