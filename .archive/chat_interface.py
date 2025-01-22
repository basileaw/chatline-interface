# chat_interface.py
import sys
import asyncio
from typing import Optional, Callable, Any

from dot_load import DotLoader
from painter import Paint, FORMATS
from scrolling_input import scrolling_input

class ChatInterface:
    """Main chat interface that coordinates all animation modules."""
    
    def __init__(self):
        """Initialize chat interface."""
        self.painter = Paint()
        self.current_content = []

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
        result, _ = scrolling_input(prompt, self.current_content)

        if get_response and result:
            # Get response generator
            response_gen = get_response(result)
            
            # Create dot loader with the input as the message
            input_loader = DotLoader(message=f"{prompt}{result}", interval=dot_interval)
            # Run the loading animation with the generator
            await input_loader.run_with_loading(response_gen)
            print(FORMATS['RESET'])
            print("\n")  # Add space after response

        return result

def run_demo():
    """Demo using real Bedrock streaming."""
    from generator import generate_stream
    
    async def demo():
        chat = ChatInterface()
        
        while True:
            def get_response(input_text):
                messages = [
                    {"role": "user", "content": input_text},
                    {"role": "system", "content": "Be helpful and concise."}
                ]
                return generate_stream(messages)
            
            user_input = await chat.chat_input(get_response=get_response)
            if user_input.lower() == 'exit':
                break
    
    asyncio.run(demo())

if __name__ == "__main__":
    run_demo()