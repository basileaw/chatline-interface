# terminal.py

import asyncio
import time
import sys
import shutil
from typing import List, Optional
from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys

class TerminalManager:
    def __init__(self, text_processor):
        self.text_processor = text_processor
        self._term_width = shutil.get_terminal_size().columns
        
        # Create key bindings
        kb = KeyBindings()
        
        @kb.add('c-e')  # Ctrl+E for edit
        def _(event):
            event.current_buffer.text = "edit"
            event.app.exit(result=event.current_buffer.text)
            
        @kb.add('c-r')  # Ctrl+R for retry
        def _(event):
            event.current_buffer.text = "retry"
            event.app.exit(result=event.current_buffer.text)
            
        # Create prompt session with key bindings
        self.prompt_session = PromptSession(
            key_bindings=kb,
            complete_while_typing=False  # Disable autocompletion for better performance
        )

    def _is_terminal(self) -> bool:
        """Check if stdout is connected to a terminal."""
        return sys.stdout.isatty()

    async def _yield_to_event_loop(self) -> None:
        """Yield control back to the event loop."""
        await asyncio.sleep(0)

    def _write(self, text: str = "", style: str = None, newline: bool = False) -> None:
        if style: sys.stdout.write(self.text_processor.get_format(style))
        sys.stdout.write(text)
        if style: sys.stdout.write(self.text_processor.get_format('RESET'))
        if newline: sys.stdout.write('\n')
        sys.stdout.flush()

    def write_and_flush(self, text: str) -> None:
        sys.stdout.write(text)
        sys.stdout.flush()

    def _cursor_control(self, show: bool) -> None:
        if self._is_terminal():
            sys.stdout.write("\033[?25h" if show else "\033[?25l")
            sys.stdout.flush()

    def _show_cursor(self) -> None: self._cursor_control(True)
    def _hide_cursor(self) -> None: self._cursor_control(False)

    def _clear_screen(self) -> None:
        if self._is_terminal():
            sys.stdout.write("\033[2J\033[H")
            sys.stdout.flush()

    def _handle_text(self, text: str, width: Optional[int] = None) -> List[str]:
        width = width or self._term_width
        result = []
        
        for para in text.split('\n'):
            if not para.strip():
                result.append('')
                continue

            line, words = '', para.split()
            for word in words:
                if len(word) > width:
                    if line: result.append(line)
                    result.extend(word[i:i+width] for i in range(0, len(word), width))
                    line = ''
                else:
                    test = f"{line}{' ' if line else ''}{word}"
                    if self.text_processor.get_visible_length(test) <= width:
                        line = test
                    else:
                        result.append(line)
                        line = word
            if line: result.append(line)
            
        return result

    async def clear(self) -> None:
        self._clear_screen()
        await self._yield_to_event_loop()

    async def write_lines(self, lines: List[str], newline: bool = True) -> None:
        for line in lines:
            self._write(line, newline=newline)
        await self._yield_to_event_loop()

    async def write_prompt(self, prompt: str, style: Optional[str] = None) -> None:
        self._write(prompt, style)
        await self._yield_to_event_loop()

    async def scroll_up(self, text: str, prompt: str, delay: float = 0.5) -> None:
        lines = self._handle_text(text)
        for i in range(len(lines) + 1):
            await self.clear()
            await self.write_lines(lines[i:])
            await self.write_prompt(prompt, 'RESET')
            await asyncio.sleep(delay)  # Keep actual sleep delay for animation

    async def update_display(self, content: str = None, prompt: str = None, 
                           preserve_cursor: bool = False) -> None:
        if not preserve_cursor: self._hide_cursor()
        await self.clear()
        if content: await self.write_lines([content], bool(prompt))
        if prompt: await self.write_prompt(prompt)
        if not preserve_cursor: self._show_cursor()

    async def write_loading_state(self, prompt: str, dots: int, dot_char: str = '.') -> None:
        self._write(f"\r{' '*80}\r{prompt}{dot_char*dots}")
        await self._yield_to_event_loop()

    async def get_user_input(self, default_text: str = "", add_newline: bool = True) -> str:
        self._show_cursor()
        if add_newline: self._write("\n")
        try:
            result = await self.prompt_session.prompt_async(
                FormattedText([('class:prompt', '> ')]), 
                default=default_text
            )
            return result.strip()
        finally:
            self._hide_cursor()

    async def handle_scroll(self, styled_lines: str, prompt: str, delay: float = 0.5) -> None:
        lines = self._handle_text(styled_lines)
        for i in range(len(lines) + 1):
            self._clear_screen()
            for ln in lines[i:]: self._write(ln, newline=True)
            self._write(self.text_processor.get_format('RESET') + prompt)
            time.sleep(delay)  # Keep actual sleep delay for animation

    async def update_animated_display(self, content: str = "", preserved_msg: str = "", 
                                   no_spacing: bool = False) -> None:
        self._clear_screen()
        if content:
            if preserved_msg:
                self._write(preserved_msg + ("" if no_spacing else "\n\n"))
            self._write(content)
        else:
            self._write(preserved_msg)
        self._write("", 'RESET')
        await self._yield_to_event_loop()