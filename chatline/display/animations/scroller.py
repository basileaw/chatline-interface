# display/animations/scroller.py

import asyncio
from typing import List, Optional

class Scroller:
    """
    Handles text scrolling animations with customizable timing and display options.
    
    Provides smooth scrolling animations for text content, handling word wrapping
    and maintaining proper terminal display formatting.
    """
    def __init__(self, style, terminal):
        """
        Initialize the scroller with style and terminal dependencies.
        
        Args:
            style: StyleEngine instance for text styling
            terminal: DisplayTerminal instance for output
        """
        self.style = style
        self.terminal = terminal

    def _handle_text(self, text: str, width: Optional[int] = None) -> List[str]:
        """
        Process text for display with word wrapping and box-drawing handling.
        
        Args:
            text: Text content to process
            width: Optional width constraint for text wrapping
            
        Returns:
            List of processed text lines
        """
        width = width or self.terminal.width
        
        # Handle box drawing characters differently
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
                    if self.style.get_visible_length(test) <= width:
                        line = test
                    else:
                        result.append(line)
                        line = word
            if line:
                result.append(line)
                
        return result

    async def scroll_up(
        self, 
        text: str, 
        prompt: str, 
        delay: float = 0.5
    ) -> None:
        """
        Scroll text upward with animation, preserving the prompt.
        
        Args:
            text: Text content to scroll
            prompt: Prompt to display after scrolling
            delay: Time delay between scroll steps in seconds
        """
        lines = self._handle_text(text)
        for i in range(len(lines) + 1):
            await self._update_scroll_display(lines[i:], prompt)
            await asyncio.sleep(delay)

    async def scroll_styled(
        self, 
        styled_lines: str, 
        prompt: str, 
        delay: float = 0.5
    ) -> None:
        """
        Scroll pre-styled text with a prompt, maintaining styling during animation.
        
        Args:
            styled_lines: Pre-styled text content to scroll
            prompt: Prompt to display after scrolling
            delay: Time delay between scroll steps in seconds
        """
        lines = self._handle_text(styled_lines)
        for i in range(len(lines) + 1):
            self.terminal.clear_screen()
            
            # Write remaining lines
            for ln in lines[i:]:
                self.terminal.write(ln, newline=True)
                
            # Write prompt with proper styling
            self.terminal.write(self.style.get_format('RESET') + prompt)
            await asyncio.sleep(delay)

    async def _update_scroll_display(self, lines: List[str], prompt: str) -> None:
        """
        Update the display during scrolling animation.
        
        Args:
            lines: Lines of text to display
            prompt: Prompt to show at the bottom
        """
        self.terminal.clear_screen()
        
        # Write lines
        for line in lines:
            self.terminal.write(line, newline=True)
            
        # Write prompt with reset formatting
        self.terminal.write(self.style.get_format('RESET'))
        self.terminal.write(prompt)