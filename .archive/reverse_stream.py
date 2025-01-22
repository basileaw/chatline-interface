# reverse_stream.py
import sys
import time
import asyncio
import textwrap
from typing import List, Optional, Tuple

class ReverseStreamer:
    """Handles reverse text streaming animations."""
    
    def __init__(self, width: int = 70):
        self.width = width
    
    @staticmethod
    def clear_screen() -> None:
        """Clear terminal screen."""
        sys.stdout.write('\033[2J\033[H')
        sys.stdout.flush()
    
    @staticmethod
    def toggle_cursor(show: bool = True) -> None:
        """Show or hide cursor."""
        sys.stdout.write('\033[?25h' if show else '\033[?25l')
        sys.stdout.flush()
    
    def display_frame(self, content: str, delay: float = 0.05) -> None:
        """Display a single animation frame."""
        self.clear_screen()
        sys.stdout.write(content)
        sys.stdout.flush()
        time.sleep(delay)

    async def reverse_stream(
        self,
        static_content: List[str],
        response_lines: List[str],
        input_text: str,
        chunk_size: int = 2,
        delay: float = 0.05
    ) -> None:
        """
        Animate text removal in reverse, word by word.
        
        Args:
            static_content: Content to preserve (e.g., demo text, previous messages)
            response_lines: Lines of text to remove in reverse
            input_text: The input text to preserve/make editable
            chunk_size: Number of words to remove per frame
            delay: Delay between frames in seconds
        """
        try:
            if not sys.stdout.isatty():
                return
                
            self.toggle_cursor(False)
            
            # Get all words from response
            text = ' '.join(response_lines)
            words = text.split()
            
            # Animate word removal
            while words:
                words = words[:-chunk_size] if len(words) > chunk_size else []
                frame_content = static_content + [f"> {input_text}"]
                if words:
                    frame_content.extend([""] + textwrap.wrap(' '.join(words), width=self.width))
                self.display_frame('\n'.join(frame_content))
                await asyncio.sleep(delay)
                
        finally:
            self.toggle_cursor(True)

def run_demo():
    """Demo of reverse text streaming."""
    demo_lines = [
        "Welcome to the reverse stream demo.",
        "Type 'exit' to quit, or 'retry' to reverse stream.",
        ""
    ]
    
    response_text = (
        "I understand you're interested in the weather forecast. "
        "Currently, we're looking at sunny conditions with a high of 75°F. "
        "The humidity is relatively low at 45%, making it quite comfortable. "
        "As for tomorrow, we're expecting some changes with partly cloudy skies "
        "developing in the afternoon. There's a 30% chance of light showers in "
        "the evening, so you might want to keep an umbrella handy."
    )
    
    last_input = None
    response_lines = textwrap.wrap(response_text, width=70)
    streamer = ReverseStreamer()
    
    while True:
        # Clear and show current state
        streamer.clear_screen()
        current_content = demo_lines.copy()
        if last_input:
            current_content.extend([f"> {last_input}", ""] + response_lines)
        print('\n'.join(current_content))
        
        # Get input
        streamer.toggle_cursor(True)
        user_input = input("> ")
        streamer.toggle_cursor(False)
        
        if user_input.lower() == 'exit':
            break
            
        if user_input.lower() == 'retry' and last_input:
            asyncio.run(streamer.reverse_stream(
                demo_lines,
                response_lines,
                last_input
            ))
        elif user_input:
            last_input = user_input
            current_content = demo_lines + [f"> {last_input}", ""] + response_lines
            streamer.display_frame('\n'.join(current_content))

if __name__ == "__main__":
    run_demo()