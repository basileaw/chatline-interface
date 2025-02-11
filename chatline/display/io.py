# display/io.py

import time
import asyncio
from typing import List, Optional

class DisplayIO:
    """Handles terminal I/O, text processing, and display updates."""
    
    def __init__(self, terminal, styles):
        """Initialize with terminal and styles."""
        self.terminal = terminal
        self.styles = styles

    def format_prompt(self, text: str) -> str:
        """Format a prompt based on user input."""
        end_char = text[-1] if text.endswith(('?', '!')) else '.'
        return f"> {text.rstrip('?.!')}{end_char * 3}"

    def _handle_text(self, text: str, width: Optional[int] = None) -> List[str]:
        """Process text for display with word wrapping and box-drawing handling."""
        width = width or self.terminal.term_width
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

    async def clear(self) -> None:
        """Clear the display."""
        self.terminal.clear_screen()
        await self._yield()

    async def write_lines(self, lines: List[str], newline: bool = True) -> None:
        """Write multiple lines to the display."""
        for line in lines:
            self.terminal.write(line, newline=newline)
        await self._yield()

    async def write_prompt(self, prompt: str, style: Optional[str] = None) -> None:
        """Write a prompt with optional style."""
        if style:
            self.terminal.write(self.styles.get_format(style))
        self.terminal.write(prompt)
        if style:
            self.terminal.write(self.styles.get_format('RESET'))
        await self._yield()

    async def write_loading_state(self, prompt: str, dots: int, dot_char: str = '.') -> None:
        """Display a loading state with dots."""
        self.terminal.write(f"\r{' ' * 80}\r{prompt}{dot_char * dots}")
        await self._yield()

    async def update_display(
        self,
        content: Optional[str] = None,
        prompt: Optional[str] = None,
        preserve_cursor: bool = False
    ) -> None:
        """Update display content and prompt, optionally preserving cursor state."""
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
        """Update display with animation support."""
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

    async def _yield(self) -> None:
        """Yield control to the event loop."""
        await asyncio.sleep(0)