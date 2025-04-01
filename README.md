# Chatline

A lightweight CLI library for building terminal-based LLM chat interfaces with minimal effort. Provides rich text styling, animations, and conversation state management.

- **Terminal UI**: Rich text formatting with styled quotes, brackets, emphasis, and more
- **Response Streaming**: Real-time streamed responses with loading animations
- **State Management**: Conversation history with edit and retry functionality
- **Dual Modes**: Run with embedded AWS Bedrock or connect to a custom backend
- **Keyboard Shortcuts**: Ctrl+E to edit previous message, Ctrl+R to retry

![](https://raw.githubusercontent.com/anotherbazeinthewall/chatline-interface/main/demo.gif)

## Installation

```bash
pip install chatline
```

With Poetry:

```bash
poetry add chatline
```

Using the embedded generator requires AWS credentials configured. You can configure AWS credentials using environment variables or by setting them in your shell configuration file.

## Usage

There are two modes: Embedded (no external dependencies) and Remote (requires response generation endpoint). 

### Embedded Mode (AWS Bedrock)

The easiest way to get started is to use the embedded generator (with AWS Bedrock):

```python
from chatline import Interface

# Initialize with embedded mode (uses AWS Bedrock)
chat = Interface()

# Add optional welcome message
chat.preface(
    "Welcome", 
    title="My App", 
    border_color="green")

# Start the conversation
chat.start()
```

### Remote Mode (Custom Backend)

However, you can also connect to a custom backend by providing the endpoint URL:

```python
from chatline import Interface

# Initialize with remote mode
chat = Interface(endpoint="http://localhost:8000/chat")

# Start the conversation with custom system and user messages
chat.start([
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello, how can you help me today?"}
])
```

#### Setting Up a Backend Server

You can use generate_stream function (or build your own) in your backend. Here's an example in a FastAPI server:

```python
import json
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from chatline import generate_stream

app = FastAPI()

# Define AWS configuration
aws_config = {
    "model_id": "anthropic.claude-3-sonnet-20240229-v1:0",
    "region": "us-east-1"  # replace with your AWS region
}

@app.post("/chat")
async def stream_chat(request: Request):
    body = await request.json()
    state = body.get('conversation_state', {})
    messages = state.get('messages', [])
    
    # Process the request and update state as needed
    state['server_turn'] = state.get('server_turn', 0) + 1
    
    # Return streaming response with updated state
    headers = {
        'Content-Type': 'text/event-stream',
        'X-Conversation-State': json.dumps(state)
    }
    
    return StreamingResponse(
        generate_stream(messages, aws_config=aws_config),  # Pass aws_config to generate_stream
        headers=headers,
        media_type="text/event-stream"
    )

if __name__ == "__main__":
    uvicorn.run("server:app", host="127.0.0.1", port=8000)
```

## License

MIT