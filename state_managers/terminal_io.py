import time
from typing import Optional, Protocol, List
from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import FormattedText

# Local protocols to avoid circular imports
class Utilities(Protocol):
    def clear_screen(self) -> None: ...
    def get_visible_length(self, text: str) -> int: ...
    def write_and_flush(self, text: str) -> None: ...
    def show_cursor(self) -> None: ...
    def hide_cursor(self) -> None: ...
    def get_terminal_width(self) -> int: ...

class Painter(Protocol):
    def get_format(self, name: str) -> str: ...

class AsyncInterfaceManager:
    """Manages user interface interactions asynchronously."""
    
    def __init__(self, utilities: Utilities, painter: Painter):
        self.utils = utilities
        self.painter = painter
        self.prompt_session = PromptSession()
        self._term_width = self.utils.get_terminal_width()

    async def get_user_input(self,
                           default_text: str = "",
                           add_newline: bool = True) -> str:
        """Get input from user with proper cursor management."""
        self.utils.show_cursor()
        
        if add_newline:
            self.utils.write_and_flush("\n")
            
        prompt = FormattedText([('class:prompt', '> ')])
        result = await self.prompt_session.prompt_async(prompt, default=default_text)
        
        self.utils.hide_cursor()
        return result.strip()

    async def handle_scroll(self, styled_lines: str, prompt: str, delay: float = 0.5) -> None:
        """Handle scrolling display with consistent timing."""
        display_lines = self._prepare_display_lines(styled_lines)
        
        for i in range(len(display_lines) + 1):
            self.utils.clear_screen()
            
            for ln in display_lines[i:]:
                self.utils.write_and_flush(ln + '\n')
                
            self.utils.write_and_flush(self.painter.get_format('RESET'))
            self.utils.write_and_flush(prompt)
            time.sleep(delay)

    def _prepare_display_lines(self, styled_lines: str) -> List[str]:
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
                if self.utils.get_visible_length(test_line) <= self._term_width:
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
        self.utils.clear_screen()
        
        if content:
            self.utils.write_and_flush(content)
            
        if prompt:
            self.utils.write_and_flush(self.painter.get_format('RESET'))
            self.utils.write_and_flush(prompt)