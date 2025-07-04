# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Development Commands
- `make embedded-client` - Run the embedded client example with default provider (Bedrock)
- `make embedded-client-log` - Run embedded client with logging enabled
- `make remote-client` - Run client connecting to remote server at localhost:8000
- `make remote-client-log` - Run remote client with logging enabled
- `make serve` - Start the example FastAPI server on localhost:8000
- `make remote-same-origin` - Run client with auto-detected same-origin endpoint
- `make release` - Release new version using utilities/release.py

### Testing Provider Generators
- `python chatline/generator.py` - Test both Bedrock and OpenRouter providers directly

## Architecture

Chatline is a Python library for building terminal-based LLM chat interfaces. The architecture consists of several key components:

### Core Components
- **Interface** (`chatline/interface.py`) - Main entry point that orchestrates all components
- **Display** (`chatline/display/`) - Handles terminal UI, styling, and animations
- **Stream** (`chatline/stream/`) - Manages streaming responses (embedded vs remote modes)
- **Conversation** (`chatline/conversation/`) - Manages chat state, history, and user interactions
- **Generator** (`chatline/generator.py`) - Handles LLM response generation with multiple providers

### Provider System
- **Base Provider** (`chatline/providers/base.py`) - Abstract base for all providers
- **Bedrock Provider** (`chatline/providers/bedrock.py`) - AWS Bedrock integration (default)
- **OpenRouter Provider** (`chatline/providers/openrouter.py`) - OpenRouter API integration

### Operation Modes
1. **Embedded Mode** - Uses built-in providers (Bedrock, OpenRouter) directly
2. **Remote Mode** - Connects to external API endpoint for response generation

### Key Design Patterns
- Provider pattern for LLM integrations with pluggable backends
- Streaming architecture supporting both local and remote generation
- Rich terminal UI with animations and styled text formatting
- Conversation state management with edit/retry/rewind functionality
- Message validation ensuring proper user/assistant alternation

### Configuration
- Uses Poetry for dependency management
- Supports AWS profiles and regions for Bedrock
- Environment variables for API keys (OPENROUTER_API_KEY)
- Logging system with file output support
- Conversation history persistence to JSON

### Keyboard Shortcuts
During conversation input, the following keyboard shortcuts are available:
- **Ctrl+E** - Edit the last user message
- **Ctrl+R** - Retry the last user message (regenerate response)
- **Ctrl+U** - Rewind conversation by one exchange (go back further in history)
- **Ctrl+P** or **Space** (on empty input) - Insert `[CONTINUE]` command
- **Ctrl+C** - Exit the conversation
- **Ctrl+D** - Exit the conversation (on empty input)

### Dependencies
- `boto3` - AWS SDK for Bedrock provider
- `httpx` - HTTP client for remote requests
- `rich` - Terminal styling and formatting
- `prompt-toolkit` - Terminal input handling
- `terminaide` - Terminal utilities (>=0.1.6)