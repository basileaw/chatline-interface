# server.py

import json
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from chatline.stream.generator import generate_stream
from chatline import DEFAULT_MESSAGES

app = FastAPI()

@app.post("/chat")
async def stream_chat(request: Request):
    """
    Process chat requests and provide streaming responses.
    
    If no messages are provided by the client, default messages will be used.
    The server always adds a 'context' field to demonstrate state persistence.
    """
    # Parse the request body
    body = await request.json()
    messages = body.get('messages', [])
    
    # Initialize state with default values
    state = {
        'turn_number': 0
    }
    
    # Use the received state if available
    if 'conversation_state' in body and body['conversation_state']:
        received_state = body['conversation_state']
        for key, value in received_state.items():
            state[key] = value
    
    # If no messages provided by client, use library defaults
    if not messages:
        print("No messages provided by client. Using library default messages.")
        messages = [
            {"role": "system", "content": DEFAULT_MESSAGES["system"]},
            {"role": "user", "content": DEFAULT_MESSAGES["user"]}
        ]
    
    # Store the messages in state
    state['messages'] = messages
    
    # Increment turn number
    state['turn_number'] += 1
    
    # Add a persistent context field (this demonstrates backend state persistence)
    state['context'] = {
        'server_version': '1.0',
        'persistent_field': 'This field persists across turns',
        'current_turn': state['turn_number']
    }
    
    # Print state info for debugging
    print(f"Turn: {state['turn_number']}, Message count: {len(messages)}")
    
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
    print("Features:")
    print("- Uses library default messages if client sends none")
    print("- Adds a persistent 'context' field to state")
    print("- Auto-reload enabled - changes to this file will restart the server\n")
    
    # Run the server with auto-reload enabled
    uvicorn.run(
        "server:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_dirs=["./"]
    )