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

### Testing Commands
- `python chatline/generator.py` - Test both Bedrock and OpenRouter providers directly
- `poetry install --with dev` - Install development dependencies including pytest
- `python -m pytest tests/ -v` - Run all tests with verbose output
- `python -m pytest tests/test_consecutive_rewind.py -v` - Run consecutive rewind functionality tests

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
- Robust conversation state management with edit/retry/rewind functionality
- Content-based state resolution for reliable consecutive rewind operations
- Message validation ensuring proper user/assistant alternation
- Atomic operation design with comprehensive error handling and rollback

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
- **Ctrl+U** - Rewind conversation by one exchange (supports unlimited consecutive rewinds)
- **Ctrl+P** or **Space** (on empty input) - Insert `[CONTINUE]` command
- **Ctrl+C** - Exit the conversation
- **Ctrl+D** - Exit the conversation (on empty input)

### Rewind Functionality
The rewind feature allows users to step back through conversation history and replay from earlier points:

#### Architecture
- **Content-Based State Resolution**: Uses message content to identify target states rather than fragile index arithmetic
- **Pre-Animation Data Extraction**: Decouples animation from state management for reliable operation
- **Atomic Operations**: Four-phase approach with comprehensive error handling and rollback
- **Unlimited Consecutive Rewinds**: Supports multiple rewind operations in sequence

#### Operation Phases
1. **Pre-flight**: Extract animation data and validate rewind possibility
2. **Animation**: Execute 3-phase visual feedback (reverse, fake reverse, fake forward)
3. **State Restoration**: Jump to content-identified target state in conversation history
4. **Message Processing**: Generate new response for the target message

#### State Management
- **Dual Message Storage**: Internal Message objects with JSON state synchronization
- **History Index Validation**: Automatic bounds checking and recovery
- **State Truncation**: History pruned at restoration point for consistency

### Testing
Comprehensive test suite covers core functionality and edge cases:

#### Test Structure
- **Unit Tests**: Individual component testing with mocked dependencies
- **Integration Tests**: End-to-end conversation flow validation
- **Rewind Tests**: Extensive consecutive rewind scenario coverage

#### Key Test Areas
- Single and multiple consecutive rewind operations
- State restoration and message synchronization
- History index validation and recovery
- Edge cases (insufficient history, empty conversations)
- Helper method validation (target message discovery, state finding)

#### Running Tests
```bash
# Install test dependencies
poetry install --with dev

# Run all tests
python -m pytest tests/ -v

# Run specific test suite
python -m pytest tests/test_consecutive_rewind.py -v

# Run with coverage (if configured)
python -m pytest tests/ --cov=chatline
```

### Dependencies
- `boto3` - AWS SDK for Bedrock provider
- `httpx` - HTTP client for remote requests
- `rich` - Terminal styling and formatting
- `prompt-toolkit` - Terminal input handling
- `terminaide` - Terminal utilities (>=0.1.6)
- `pytest` - Testing framework (dev dependency)
- `pytest-asyncio` - Async test support (dev dependency)