# state/new_terminal.py
import asyncio
import time
from typing import List, Optional, Protocol
from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import FormattedText

class Utilities(Protocol):
    def clear_screen(self) -> None: ...
    def get_visible_length(self, text: str) -> int: ...
    def write_and_flush(self, text: str) -> None: ...
    def hide_cursor(self) -> None: ...
    def show_cursor(self) -> None: ...
    def get_terminal_width(self) -> int: ...

class Painter(Protocol):
    def get_format(self, name: str) -> str: ...

class TerminalManager:
    """Manages terminal display and user input operations."""
    
    def __init__(self, utilities: Utilities, painter: Painter):
        self.utils = utilities
        self.painter = painter
        self.prompt_session = PromptSession()
        self._term_width = self.utils.get_terminal_width()

    # Screen operations from AsyncScreenManager
    async def clear(self):
        """Clear the screen asynchronously."""
        self.utils.clear_screen()
        await asyncio.sleep(0)

    async def write_lines(self, lines: List[str], add_newline: bool = True):
        """Write multiple lines to the screen."""
        for line in lines:
            self.utils.write_and_flush(line)
            if add_newline:
                self.utils.write_and_flush('\n')
        await asyncio.sleep(0)

    async def write_prompt(self, prompt: str, style: Optional[str] = None):
        """Write a prompt with optional styling."""
        if style:
            self.utils.write_and_flush(style)
        self.utils.write_and_flush(prompt)
        if style:
            self.utils.write_and_flush(self.painter.get_format('RESET'))
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
                if self.utils.get_visible_length(test_line) <= self._term_width:
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
            await self.write_prompt(prompt, self.painter.get_format('RESET'))
            await asyncio.sleep(delay)

    async def update_display(self,
                           content: Optional[str] = None,
                           prompt: Optional[str] = None,
                           preserve_cursor: bool = False):
        """Update the entire display."""
        if not preserve_cursor:
            self.utils.hide_cursor()
        await self.clear()
        if content:
            await self.write_lines([content], add_newline=bool(prompt))
        if prompt:
            await self.write_prompt(prompt)
        if not preserve_cursor:
            self.utils.show_cursor()

    async def write_loading_state(self, prompt: str, dots: int):
        """Write a loading state with dots."""
        self.utils.write_and_flush(f"\r{' '*80}\r{prompt}{'.'*dots}")
        await asyncio.sleep(0)

    # Interface operations from AsyncInterfaceManager
    async def get_user_input(self, default_text: str = "", add_newline: bool = True) -> str:
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