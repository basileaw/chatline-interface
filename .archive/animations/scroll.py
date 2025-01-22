# animations/scroll.py
import sys
import time
from typing import List
from .base import TerminalAnimation
from output_handler import FORMATS

class ScrollAnimation(TerminalAnimation):
    """Handles scroll-up animation."""
    
    async def animate(self, styled_lines: str, prompt: str, delay: float = 0.1) -> None:
        """Scroll text upward with preserved styling."""
        lines = styled_lines.splitlines()
        for i in range(len(lines)+1):
            self.clear_screen()
            for ln in lines[i:]:
                sys.stdout.write(ln + '\n')
            if i < len(lines):
                sys.stdout.write('\n')
            sys.stdout.write(FORMATS['RESET'])  # Reset formatting for prompt
            sys.stdout.write(prompt)
            sys.stdout.flush()
            time.sleep(delay)