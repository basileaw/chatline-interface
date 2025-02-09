# display/io.py

import asyncio
import time
from typing import List, Optional, Any

class DisplayIO:
    """
    Handles input/output operations for terminal display.
    
    This class manages text processing, display updates, and scrolling
    effects while coordinating with the terminal and styles components.
    """
    def __init__(self, terminal, styles):
        """
        Initialize display I/O handler.
        
        Args:
            terminal: Terminal interface for display operations
            styles: Styles interface for text formatting
        """
        self.terminal = terminal
        self.styles = styles

    def _handle_text(self, text: str, width: Optional[int] = None) -> List[str]:
        """
        Process text for display, handling word wrapping and special characters.
        
        Args:
            text: Text to process
            width: Optional width constraint (defaults to terminal width)
            
        Returns:
            List of processed text lines
        """
        width = width or self.terminal.term_width
        
        # Handle box-drawing characters differently
        if any(x in text for x in ('╭','╮','╯','╰')):
            return text.split('\n')
        
        result = []
        for para in text.split('\n'):
            if not para.strip():
                result.append('')
                continue
                
            line, words = '', para.split()
            for word in words:
                if len(word) > width:
                    # Handle words longer than width
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

    async def clear(self) -> None:
        """Clear the display."""
        self.terminal.clear_screen()
        await self._yield()

    async def write_lines(self, lines: List[str], newline: bool = True) -> None:
        """
        Write multiple lines to display.
        
        Args:
            lines: List of text lines to write
            newline: Whether to append newline to each line
        """
        for line in lines:
            self.terminal.write(line, newline=newline)
        await self._yield()

    async def write_prompt(self, prompt: str, style: Optional[str] = None) -> None:
        """
        Write prompt text with optional styling.
        
        Args:
            prompt: Prompt text to display
            style: Optional style to apply
        """
        if style:
            self.terminal.write(self.styles.get_format(style))
        self.terminal.write(prompt)
        if style:
            self.terminal.write(self.styles.get_format('RESET'))
        await self._yield()

    async def write_loading_state(
        self,
        prompt: str,
        dots: int,
        dot_char: str = '.'
    ) -> None:
        """
        Update loading state display.
        
        Args:
            prompt: Base prompt text
            dots: Number of dots to display
            dot_char: Character to use for dots
        """
        self.terminal.write(f"\r{' '*80}\r{prompt}{dot_char*dots}")
        await self._yield()

    async def update_display(
        self,
        content: Optional[str] = None,
        prompt: Optional[str] = None,
        preserve_cursor: bool = False
    ) -> None:
        """
        Update display content and prompt.
        
        Args:
            content: Optional main content
            prompt: Optional prompt text
            preserve_cursor: Whether to preserve cursor state
        """
        if not preserve_cursor:
            self.terminal.hide_cursor()
            
        await self.clear()
        
        if content:
            await self.write_lines([content], bool(prompt))
        if prompt:
            await self.write_prompt(prompt)
            
        if not preserve_cursor:
            self.terminal.hide_cursor()

    async def update_animated_display(
        self,
        content: str = "",
        preserved_msg: str = "",
        no_spacing: bool = False
    ) -> None:
        """
        Update display with animation support.
        
        Args:
            content: Main content to display
            preserved_msg: Message to preserve at top
            no_spacing: Whether to remove extra spacing
        """
        self.terminal.clear_screen()
        
        if content:
            if preserved_msg:
                self.terminal.write(preserved_msg + ("" if no_spacing else "\n\n"))
            self.terminal.write(content)
        else:
            self.terminal.write(preserved_msg)
            
        self.terminal.write("", newline=False)
        self.terminal.write(self.styles.get_format('RESET'))
        await self._yield()

    async def scroll_up(
        self,
        text: str,
        prompt: str,
        delay: float = 0.5
    ) -> None:
        """
        Scroll text upward with animation.
        
        Args:
            text: Text to scroll
            prompt: Prompt to display
            delay: Delay between scroll steps
        """
        lines = self._handle_text(text)
        for i in range(len(lines) + 1):
            await self.clear()
            await self.write_lines(lines[i:])
            await self.write_prompt(prompt, 'RESET')
            await asyncio.sleep(delay)

    async def handle_scroll(
        self,
        styled_lines: str,
        prompt: str,
        delay: float = 0.5
    ) -> None:
        """
        Handle scrolling of styled text.
        
        Args:
            styled_lines: Pre-styled text to scroll
            prompt: Prompt to display
            delay: Delay between scroll steps
        """
        lines = self._handle_text(styled_lines)
        for i in range(len(lines) + 1):
            self.terminal.clear_screen()
            for ln in lines[i:]:
                self.terminal.write(ln, newline=True)
            self.terminal.write(
                self.styles.get_format('RESET') + prompt
            )
            time.sleep(delay)

    async def _yield(self) -> None:
        """Yield to event loop briefly."""
        await asyncio.sleep(0)