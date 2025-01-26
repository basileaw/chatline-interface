# async_screen_manager.py

import asyncio
import shutil
from typing import List, Optional
from utilities import (
    clear_screen,
    get_visible_length,
    write_and_flush,
    manage_cursor
)
from painter import FORMATS

class AsyncScreenManager:
    """Manages all screen-related operations asynchronously."""
    
    def __init__(self):
        self._term_width = shutil.get_terminal_size().columns
        
    async def clear(self):
        """Clear the screen asynchronously."""
        clear_screen()
        await asyncio.sleep(0)
        
    async def write_lines(self, lines: List[str], add_newline: bool = True):
        """Write multiple lines to the screen."""
        for line in lines:
            write_and_flush(line)
            if add_newline:
                write_and_flush('\n')
        await asyncio.sleep(0)
        
    async def write_prompt(self, prompt: str, style: Optional[str] = None):
        """Write a prompt with optional styling."""
        if style:
            write_and_flush(style)
        write_and_flush(prompt)
        if style:
            write_and_flush(FORMATS['RESET'])
        await asyncio.sleep(0)
        
    def _prepare_display_lines(self, styled_text: str) -> List[str]:
        """Prepare text for display with proper line wrapping."""
        paragraphs = styled_text.split('\n')
        display_lines = []
        
        for paragraph in paragraphs:
            if not paragraph.strip():
                display_lines.append('')
                continue
                
            current_line = ''
            words = paragraph.split()
            
            for word in words:
                test_line = current_line + (' ' if current_line else '') + word
                if get_visible_length(test_line) <= self._term_width:
                    current_line = test_line
                else:
                    display_lines.append(current_line)
                    current_line = word
                    
            if current_line:
                display_lines.append(current_line)
                
        return display_lines
        
    async def scroll_up(self, styled_text: str, prompt: str, delay: float = 0.5):
        """Scroll text upward with smooth animation."""
        display_lines = self._prepare_display_lines(styled_text)
        
        for i in range(len(display_lines) + 1):
            await self.clear()
            await self.write_lines(display_lines[i:])
            await self.write_prompt(prompt, FORMATS['RESET'])
            await asyncio.sleep(delay)
            
    async def update_display(self, 
                           content: Optional[str] = None,
                           prompt: Optional[str] = None,
                           preserve_cursor: bool = False):
        """Update the entire display."""
        if not preserve_cursor:
            manage_cursor(False)
            
        await self.clear()
        
        if content:
            await self.write_lines([content], add_newline=bool(prompt))
            
        if prompt:
            await self.write_prompt(prompt)
            
        if not preserve_cursor:
            manage_cursor(True)
            
    async def write_loading_state(self, prompt: str, dots: int):
        """Write a loading state with dots."""
        write_and_flush(f"\r{' '*80}\r{prompt}{'.'*dots}")
        await asyncio.sleep(0)