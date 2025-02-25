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
    
    This server directly modifies the state received from the frontend.
    If no state or messages are provided, it initializes with defaults.
    """
    # Parse the request body
    body = await request.json()
    
    # Get state from the request, or initialize a new one if none exists
    state = body.get('conversation_state', {})
    
    # Extract or set default messages
    messages = state.get('messages', [])
    if not messages:
        print("No messages provided. Using library default messages.")
        messages = DEFAULT_MESSAGES
        state['messages'] = messages
    
    # Just increment the server turn counter
    state['server_turn'] = state.get('server_turn', 0) + 1
    
    # Print state info for debugging
    print(f"Server turn: {state['server_turn']}")
    print(f"Message count: {len(messages)}")
    
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
    print("- Directly modifies state received from frontend")
    print("- Uses library default messages if none provided")
    print("- Minimal state management - just tracks server turns")
    print("- Auto-reload enabled - changes to this file will restart the server\n")
    
    # Run the server with auto-reload enabled
    uvicorn.run(
        "server:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_dirs=["./"]
    )