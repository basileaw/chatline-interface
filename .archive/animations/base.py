# animations/base.py

import sys
import time
from abc import ABC, abstractmethod
from typing import List, Optional

class TerminalAnimation(ABC):
    """Base class for terminal animations."""
    
    @staticmethod
    def clear_screen() -> None:
        if sys.stdout.isatty():
            sys.stdout.write("\033[2J\033[H")
            sys.stdout.flush()
    
    @staticmethod
    def hide_cursor() -> None:
        if sys.stdout.isatty():
            sys.stdout.write("\033[?25l")
            sys.stdout.flush()
    
    @staticmethod
    def show_cursor() -> None:
        if sys.stdout.isatty():
            sys.stdout.write("\033[?25h")
            sys.stdout.flush()
            
    def display_frame(self, content: str, delay: float = 0.05) -> None:
        """Display a single animation frame."""
        self.clear_screen()
        sys.stdout.write(content)
        sys.stdout.flush()
        time.sleep(delay)

    @abstractmethod
    async def animate(self, *args, **kwargs) -> None:
        """Run the animation."""
        pass