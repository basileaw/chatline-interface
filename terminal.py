# terminal.py

import asyncio
import time
import sys
import shutil
from typing import List, Optional
from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import FormattedText

class TerminalManager:
    """Manages all terminal-related operations including I/O, display, and cursor management."""
    
    def __init__(self, text_processor):
        """Initialize TerminalManager with text processor dependency."""
        self.text_processor = text_processor
        self.prompt_session = PromptSession()
        self._term_width = self._get_terminal_width()

    def _get_terminal_width(self) -> int:
        """Get current terminal width."""
        return shutil.get_terminal_size().columns

    def _write(self, text: str = "", style: str = None, newline: bool = False) -> None:
        """Internal method to write to stdout and flush."""
        if style:
            sys.stdout.write(self.text_processor.get_format(style))
        sys.stdout.write(text)
        if style:
            sys.stdout.write(self.text_processor.get_format('RESET'))
        if newline:
            sys.stdout.write('\n')
        sys.stdout.flush()

    def write_and_flush(self, text: str) -> None:
        """Write text to stdout and flush buffer."""
        sys.stdout.write(text)
        sys.stdout.flush()

    def _show_cursor(self) -> None:
        """Show the terminal cursor."""
        if sys.stdout.isatty():
            sys.stdout.write("\033[?25h")
            sys.stdout.flush()

    def _hide_cursor(self) -> None:
        """Hide the terminal cursor."""
        if sys.stdout.isatty():
            sys.stdout.write("\033[?25l")
            sys.stdout.flush()

    def _clear_screen(self) -> None:
        """Clear the terminal screen and reset cursor position."""
        if sys.stdout.isatty():
            sys.stdout.write("\033[2J\033[H")
            sys.stdout.flush()

    def _handle_long_word(self, word: str, width: Optional[int] = None) -> List[str]:
        """Split a word that exceeds terminal width into chunks."""
        if width is None:
            width = self._get_terminal_width()
        chunks = []
        while word:
            if len(word) <= width:
                chunks.append(word)
                break
            chunks.append(word[:width])
            word = word[width:]
        return chunks

    def _prepare_lines(self, text: str) -> List[str]:
        """Prepare text for display with proper line wrapping."""
        lines = []
        for para in text.split('\n'):
            if not para.strip():
                lines.append('')
                continue
            line = ''
            for word in para.split():
                test = line + (' ' if line else '') + word
                if self.text_processor.get_visible_length(test) <= self._term_width:
                    line = test
                else:
                    lines.append(line)
                    line = word
            if line:
                lines.append(line)
        return lines

    async def clear(self) -> None:
        """Clear the screen asynchronously."""
        self._clear_screen()
        await asyncio.sleep(0)

    async def write_lines(self, lines: List[str], newline: bool = True) -> None:
        """Write multiple lines to the screen."""
        for line in lines:
            self._write(line, newline=newline)
        await asyncio.sleep(0)

    async def write_prompt(self, prompt: str, style: Optional[str] = None) -> None:
        """Write a prompt with optional styling."""
        self._write(prompt, style)
        await asyncio.sleep(0)

    async def scroll_up(self, text: str, prompt: str, delay: float = 0.5) -> None:
        """Scroll text upward with smooth animation."""
        lines = self._prepare_lines(text)
        for i in range(len(lines) + 1):
            await self.clear()
            await self.write_lines(lines[i:])
            await self.write_prompt(prompt, 'RESET')
            await asyncio.sleep(delay)

    async def update_display(self, content: str = None, prompt: str = None, 
                           preserve_cursor: bool = False) -> None:
        """Update the entire display."""
        if not preserve_cursor:
            self._hide_cursor()
        await self.clear()
        if content:
            await self.write_lines([content], bool(prompt))
        if prompt:
            await self.write_prompt(prompt)
        if not preserve_cursor:
            self._show_cursor()

    async def write_loading_state(self, prompt: str, dots: int) -> None:
        """Write a loading state with dots."""
        self._write(f"\r{' '*80}\r{prompt}{'.'*dots}")
        await asyncio.sleep(0)

    async def get_user_input(self, default_text: str = "", add_newline: bool = True) -> str:
        """Get input from user with proper cursor management."""
        self._show_cursor()
        if add_newline:
            self._write("\n")  # Add single newline before input prompt
        prompt = FormattedText([('class:prompt', '> ')])
        result = await self.prompt_session.prompt_async(prompt, default=default_text)
        self._hide_cursor()
        return result.strip()

    async def handle_scroll(self, styled_lines: str, prompt: str, delay: float = 0.5) -> None:
        """Handle scrolling display with consistent timing."""
        lines = self._prepare_lines(styled_lines)
        for i in range(len(lines) + 1):
            self._clear_screen()
            for ln in lines[i:]:
                self._write(ln, newline=True)
            self._write(self.text_processor.get_format('RESET') + prompt)
            time.sleep(delay)

    async def update_animated_display(self, content: str = "", preserved_msg: str = "", 
                                   no_spacing: bool = False) -> None:
        """Update the terminal screen with formatted content during animations."""
        self._clear_screen()
        if content:
            if preserved_msg:
                self._write(preserved_msg + ("" if no_spacing else "\n\n"))
            self._write(content)
        else:
            self._write(preserved_msg)
        self._write("", 'RESET')
        await asyncio.sleep(0.01)