# server.py

import json
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from chatline.stream.generator import generate_stream

app = FastAPI()

@app.post("/chat")
async def stream_chat(request: Request):
    """
    Simple example endpoint for Chatline interface.
    
    This server:
    1. Receives messages and state from the client
    2. Generates a streaming response
    3. Adds a persistent 'context' field to the state
    4. Returns the updated state in the X-Conversation-State header
    """
    # Parse the request body
    body = await request.json()
    messages = body.get('messages', [])
    
    # Initialize state with default values
    state = {
        'messages': messages,
        'turn_number': 0
    }
    
    # Use the received state if available
    if 'conversation_state' in body and body['conversation_state']:
        received_state = body['conversation_state']
        for key, value in received_state.items():
            state[key] = value
    
    # Increment turn number
    state['turn_number'] += 1
    
    # Add a persistent context field (this demonstrates backend state persistence)
    state['context'] = {
        'server_version': '1.0',
        'persistent_field': 'This field persists across turns',
        'current_turn': state['turn_number']
    }
    
    # Print state info for debugging
    print(f"Turn: {state['turn_number']}, State keys: {list(state.keys())}")
    
    # Create response with the updated state
    headers = {
        'Content-Type': 'text/event-stream',
        'X-Conversation-State': json.dumps(state)
    }
    
    # Return streaming response
    return StreamingResponse(
        generate_stream(messages),
        headers=headers,
        media_type="text/event-stream"
    )

if __name__ == "__main__":
    print("\n=== Chatline Example Server ===")
    print("Endpoint: http://127.0.0.1:8000/chat")
    print("This server adds a persistent 'context' field to demonstrate state management")
    print("Auto-reload is enabled - changes to this file will restart the server\n")
    
    # Run the server with auto-reload enabled
    uvicorn.run(
        "server:app",  # Import string (file:app_variable)
        host="127.0.0.1",
        port=8000,
        reload=True,  # Enable auto-reload on file changes
        reload_dirs=["./"]  # Directories to watch for changes
    )