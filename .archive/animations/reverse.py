# animations/reverse.py
import sys
import asyncio
from typing import List
from .base import TerminalAnimation
from output_handler import FORMATS

class ReverseAnimation(TerminalAnimation):
    """Handles reverse text streaming animations."""
    
    def __init__(self, width: int = 70):
        self.width = width
    
    async def animate(
        self,
        static_content: List[str],
        response_lines: List[str],
        input_text: str,
        chunk_size: int = 2,
        delay: float = 0.05
    ) -> None:
        """Animate text removal in reverse, preserving only input line."""
        if not sys.stdout.isatty():
            return
            
        try:
            self.hide_cursor()
            
            # Extract only the parts we want
            input_line = response_lines[0]  # The "> command..." line with dots
            content_lines = response_lines[2:]  # Skip input line and blank line
            
            # Display initial state
            current_lines = [input_line, ""] + content_lines
            self.display_frame('\n'.join(current_lines))
            await asyncio.sleep(delay)
            
            # Remove content lines from bottom up
            while content_lines:
                content_lines = content_lines[:-chunk_size] if len(content_lines) > chunk_size else []
                current_lines = [input_line, ""] + content_lines
                self.display_frame('\n'.join(current_lines))
                await asyncio.sleep(delay)
            
            # Final frame with just input line and newline
            self.display_frame(input_line)
            
        finally:
            self.show_cursor()