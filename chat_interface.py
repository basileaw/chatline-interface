# chat_interface.py
import sys
import asyncio
from typing import List, Optional, Callable, Any, Dict, Tuple

from scrolling_input import ScrollingInput
from dot_load import DotLoader
from painter import Paint, FORMATS
from reverse_stream import ReverseStreamer

class ChatInterface:
    """
    Main chat interface that coordinates all animation modules.
    """
    
    def __init__(self):
        """Initialize chat interface."""
        # Initialize with empty demo content - we'll update it per conversation
        self.scroller = ScrollingInput(demo_content=[])
        self.painter = Paint()
        self.current_content = []
        self.last_input = None
        self.last_response = []

    async def chat_input(
        self,
        prompt: str = "> ",
        get_response: Optional[Callable[[str], Any]] = None,
        dot_interval: float = 0.75
    ) -> str:
        """
        Get user input with scrolling animation, then show loading dots using the input text
        while waiting for and processing the response.
        """
        # Get input with scrolling animation
        result, new_content = self.scroller.get_input(
            prompt=prompt,
            content_lines=self.current_content
        )
        self.current_content = new_content if new_content else self.current_content
        self.last_input = result

        if get_response and result:
            # Create a dot loader using the input text as the message and wait for response
            input_loader = DotLoader(message=f"{prompt}{result}", interval=dot_interval)
            # Get the generator from the callback
            response_gen = get_response(result)
            await input_loader.run_with_loading(response_gen)
            print(FORMATS['RESET'])

        return result

def run_demo():
    """Demo showcasing the chat interface functionality."""
    from generator import generate_stream
    
    async def demo():
        chat = ChatInterface()
        
        def get_response(input_text):
            messages = [
                {
                    "role": "system",
                    "content": 'Write a helpful, friendly response.'
                },
                {
                    "role": "user",
                    "content": input_text
                }
            ]
            return generate_stream(messages)
        
        while True:
            user_input = await chat.chat_input(get_response=get_response)
            
            if user_input.lower() == 'exit':
                break
    
    asyncio.run(demo())

if __name__ == "__main__":
    run_demo()