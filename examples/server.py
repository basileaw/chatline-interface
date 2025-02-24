# server.py

import json
import uvicorn
import random
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from chatline.stream.generator import generate_stream

app = FastAPI()

@app.post("/chat")
async def stream_chat(request: Request):
    """Handle chat requests."""
    # Parse the request body and handle potential None cases
    body = await request.json()
    messages = body.get('messages', [])
    
    # Get the state from the request, defaulting to an empty state if not present
    state = {
        'messages': messages,
        'turn_number': 0
    }
    
    # If we received state information, update our state
    if 'conversation_state' in body and body['conversation_state']:
        received_state = body['conversation_state']
        # Update state with received data
        for key, value in received_state.items():
            state[key] = value
    
    # Increment the turn number
    state['turn_number'] += 1
    
    # Add a context field on every third turn for testing
    if state['turn_number'] % 3 == 0:
        state["context"] = {
            "sentiment": "positive",
            "topics": ["chat", "ai", "programming"],
            "importance": random.uniform(0.5, 1.0)
        }
    
    # Create response with the updated state
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
    print("Starting server on http://127.0.0.1:8000/chat")
    print("This server will add a context field every third turn")
    print("to demonstrate preserving backend-added fields")
    uvicorn.run(app, host="127.0.0.1", port=8000)