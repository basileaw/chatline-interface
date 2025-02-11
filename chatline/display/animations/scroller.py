# animations/scroller.py

import asyncio
import time
from typing import List, Optional

class Scroller:
    """Handles text scrolling animations with customizable timing and display options."""
    
    def __init__(self, styles, utilities=None):
        """
        Initialize the scroller with style and utility dependencies.
        
        Args:
            styles: DisplayStyles instance for text styling
            utilities: DisplayIO instance for terminal operations
        """
        self.styles = styles
        self.utilities = utilities
        
    def _handle_text(self, text: str, width: Optional[int] = None) -> List[str]:
        """
        Process text for display with word wrapping and box-drawing handling.
        
        Args:
            text: Text content to process
            width: Optional width constraint for text wrapping
            
        Returns:
            List of processed text lines
        """
        width = width or self.utilities.terminal.term_width
        if any(ch in text for ch in ('╭', '╮', '╯', '╰')):
            return text.split('\n')
        
        result = []
        for para in text.split('\n'):
            if not para.strip():
                result.append('')
                continue

            line, words = '', para.split()
            for word in words:
                if len(word) > width:
                    if line:
                        result.append(line)
                    result.extend(word[i:i+width] for i in range(0, len(word), width))
                    line = ''
                else:
                    test = f"{line}{' ' if line else ''}{word}"
                    if self.styles.get_visible_length(test) <= width:
                        line = test
                    else:
                        result.append(line)
                        line = word
            if line:
                result.append(line)
        return result

    async def scroll_up(self, text: str, prompt: str, delay: float = 0.5) -> None:
        """
        Scroll text upward with animation, preserving the prompt.
        
        Args:
            text: Text content to scroll
            prompt: Prompt to display after scrolling
            delay: Time delay between scroll steps in seconds
        """
        lines = self._handle_text(text)
        for i in range(len(lines) + 1):
            await self.utilities.clear()
            await self.utilities.write_lines(lines[i:])
            await self.utilities.write_prompt(prompt, 'RESET')
            await asyncio.sleep(delay)

    async def scroll_styled(self, styled_lines: str, prompt: str, delay: float = 0.5) -> None:
        """
        Scroll pre-styled text with a prompt, maintaining styling during animation.
        
        Args:
            styled_lines: Pre-styled text content to scroll
            prompt: Prompt to display after scrolling
            delay: Time delay between scroll steps in seconds
        """
        lines = self._handle_text(styled_lines)
        for i in range(len(lines) + 1):
            self.utilities.terminal.clear_screen()
            for ln in lines[i:]:
                self.utilities.terminal.write(ln, newline=True)
            self.utilities.terminal.write(self.styles.get_format('RESET') + prompt)
            await asyncio.sleep(delay)