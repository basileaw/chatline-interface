# test_client.py

import asyncio
import httpx
import json
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("test_client")

async def test_server_connection(url="http://127.0.0.1:8000/chat"):
    """Test the connection to the server with a simple message."""
    
    # Sample messages for testing
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello, how are you?"}
    ]
    
    # Create the payload
    payload = {
        "messages": messages,
        "conversation_state": {
            "turn_number": 0
        }
    }
    
    logger.info(f"Connecting to server at {url}")
    logger.debug(f"Sending payload: {json.dumps(payload, indent=2)}")
    
    try:
        async with httpx.AsyncClient() as client:
            logger.info("Making POST request...")
            response = await client.post(
                url,
                json=payload,
                timeout=30.0
            )
            
            logger.info(f"Response status: {response.status_code}")
            logger.debug(f"Response headers: {response.headers}")
            
            # Try to read some of the streaming response
            logger.info("Reading response stream...")
            content = await response.aread()
            logger.debug(f"Response content (first 500 bytes): {content[:500]}")
            
            # Check for conversation state header
            if 'X-Conversation-State' in response.headers:
                state = json.loads(response.headers['X-Conversation-State'])
                logger.info(f"Received conversation state with keys: {list(state.keys())}")
                logger.debug(f"Complete state: {json.dumps(state, indent=2)}")
            else:
                logger.warning("No conversation state header found in response")
                
            return True
    except Exception as e:
        logger.error(f"Error connecting to server: {e}")
        return False

async def main():
    """Run the test client."""
    logger.info("Starting test client")
    
    # Test with /chat endpoint
    success = await test_server_connection("http://127.0.0.1:8000/chat")
    
    # If that failed, try with root endpoint
    if not success:
        logger.info("Testing alternative endpoint...")
        await test_server_connection("http://127.0.0.1:8000")
    
    logger.info("Test complete")

if __name__ == "__main__":
    asyncio.run(main())