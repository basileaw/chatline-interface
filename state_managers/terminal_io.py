# state_managers/terminal_io.py

import time
import shutil
from typing import Optional
from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import FormattedText
from utilities import (
    clear_screen,
    get_visible_length,
    write_and_flush,
    manage_cursor
)
from streaming_output.painter import FORMATS

class AsyncInterfaceManager:
    """Manages user interface interactions asynchronously."""
    
    def __init__(self):
        self.prompt_session = PromptSession()
        self._term_width = shutil.get_terminal_size().columns
        
    async def get_user_input(self, 
                            default_text: str = "", 
                            add_newline: bool = True) -> str:
        """Get input from user with proper cursor management."""
        manage_cursor(True)
        if add_newline:
            write_and_flush("\n")
            
        prompt = FormattedText([('class:prompt', '> ')])
        result = await self.prompt_session.prompt_async(prompt, default=default_text)
        manage_cursor(False)
        return result.strip()
        
    async def handle_scroll(self, styled_lines: str, prompt: str, delay: float = 0.5) -> None:
        """Handle scrolling display with consistent timing."""
        display_lines = self._prepare_display_lines(styled_lines)
        
        for i in range(len(display_lines) + 1):
            clear_screen()
            for ln in display_lines[i:]:
                write_and_flush(ln + '\n')
            write_and_flush(FORMATS['RESET'])
            write_and_flush(prompt)
            time.sleep(delay)
            
    def _prepare_display_lines(self, styled_lines: str) -> list[str]:
        """Prepare text for display with proper line wrapping."""
        paragraphs = styled_lines.split('\n')
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
        
    async def update_screen(self, content: Optional[str] = None, 
                           prompt: Optional[str] = None) -> None:
        """Update screen content with optional prompt."""
        clear_screen()
        if content:
            write_and_flush(content)
        if prompt:
            write_and_flush(FORMATS['RESET'])
            write_and_flush(prompt)