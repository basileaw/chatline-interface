# Chatline

[![PyPI](https://img.shields.io/pypi/v/chatline.svg)](https://pypi.org/project/chatline/) [![License: MIT](https://img.shields.io/badge/license-MIT-blue)](https://opensource.org/licenses/MIT) [![Demo chat.alexbasile.com](https://img.shields.io/badge/Demo%20at-chat.alexbasile.com-blue)](https://chat.alexbasile.com)

A lightweight CLI library for building terminal-based LLM chat interfaces with minimal effort. Provides rich text styling, animations, and conversation state management.

![](https://raw.githubusercontent.com/anotherbazeinthewall/chatline-interface/main/demo.gif)

## Installation

```bash
pip install chatline
```

With Poetry:

```bash
poetry add chatline
```

## Usage

### Embedded Mode (AWS Bedrock)

For quick prototyping with AWS Bedrock:

```python
from chatline import Interface

# Initialize with embedded mode (uses AWS Bedrock)
chat = Interface(logging_enabled=True)

# Add optional welcome message
chat.preface("Welcome to the Demo", title="My App", border_color="green")

# Start the conversation
chat.start()
```

### Remote Mode (Custom Backend)

Connect to your own FastAPI/HTTP backend:

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

### Setting Up a Backend Server

Example FastAPI server:

```python
# server.py
import json
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from chatline import generate_stream

app = FastAPI()

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
        generate_stream(messages),
        headers=headers,
        media_type="text/event-stream"
    )

if __name__ == "__main__":
    uvicorn.run("server:app", host="127.0.0.1", port=8000)
```

## Features

- **Terminal UI**: Rich text formatting with styled quotes, brackets, emphasis, and more
- **Response Streaming**: Real-time streamed responses with loading animations
- **State Management**: Conversation history with edit and retry functionality
- **Dual Modes**: Run with embedded AWS Bedrock or connect to a custom backend
- **Keyboard Shortcuts**: Ctrl+E to edit previous message, Ctrl+R to retry

## Dependencies

- Python ≥ 3.12
- AWS credentials configured (for embedded mode with Bedrock)
- boto3, httpx, rich, prompt-toolkit

## License

MIT