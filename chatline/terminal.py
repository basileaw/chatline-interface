# terminal.py

import asyncio, time, sys, shutil
from typing import List, Optional, ContextManager
from contextlib import contextmanager
from prompt_toolkit import PromptSession
from prompt_toolkit.validation import Validator, ValidationError
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.key_binding import KeyBindings

class Terminal:
    def __init__(self, styles):
        self.styles = styles
        self.term_width = shutil.get_terminal_size().columns
        self._is_edit_mode = False
        self._cursor_visible = True
        kb = KeyBindings()

        @kb.add('c-e')
        def _(event):
            if not self._is_edit_mode:
                event.current_buffer.text = "edit"
                event.app.exit(result=event.current_buffer.text)

        @kb.add('c-r')
        def _(event):
            if not self._is_edit_mode:
                event.current_buffer.text = "retry"
                event.app.exit(result=event.current_buffer.text)

        self.prompt_session = PromptSession(key_bindings=kb, complete_while_typing=False)

    def _is_terminal(self) -> bool:
        return sys.stdout.isatty()

    async def _yield_to_event_loop(self) -> None:
        await asyncio.sleep(0)

    class CursorContext:
        def __init__(self, terminal, show: bool):
            self.terminal = terminal
            self.show = show

        def __enter__(self):
            if self.terminal._cursor_visible != self.show:
                self.terminal._cursor_visible = self.show
                if self.terminal._is_terminal():
                    sys.stdout.write("\033[?25h" if self.show else "\033[?25l")
                    sys.stdout.flush()
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            if not self.show and self.terminal._cursor_visible:
                self.terminal._cursor_visible = False
                if self.terminal._is_terminal():
                    sys.stdout.write("\033[?25l")
                    sys.stdout.flush()

    def cursor_control(self, show: bool) -> 'Terminal.CursorContext':
        """Control cursor visibility."""
        return self.CursorContext(self, show)

    def _show_cursor(self) -> None:
        with self.cursor_control(True):
            pass

    def _hide_cursor(self) -> None:
        with self.cursor_control(False):
            pass

    def _write(self, text: str = "", style: Optional[str] = None, newline: bool = False) -> None:
        """Consolidated write method with optional styling."""
        with self.cursor_control(False):
            if style:
                sys.stdout.write(self.styles.get_format(style))
            sys.stdout.write(text)
            if style:
                sys.stdout.write(self.styles.get_format('RESET'))
            if newline:
                sys.stdout.write('\n')
            sys.stdout.flush()

    def _clear_screen(self) -> None:
        """Clear the terminal screen."""
        if self._is_terminal():
            self._write("\033[2J\033[H")

    def _handle_text(self, text: str, width: Optional[int] = None) -> List[str]:
        """Handle text wrapping with special character preservation."""
        width = width or self.term_width
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
        """Scroll text upward with animation."""
        lines = self._handle_text(text)
        for i in range(len(lines)+1):
            await self.clear()
            await self.write_lines(lines[i:])
            await self.write_prompt(prompt, 'RESET')
            await asyncio.sleep(delay)

    async def update_display(self, content: str = None, prompt: str = None, preserve_cursor: bool = False) -> None:
        with self.cursor_control(preserve_cursor):
            await self.clear()
            if content:
                await self.write_lines([content], bool(prompt))
            if prompt:
                await self.write_prompt(prompt)

    async def write_loading_state(self, prompt: str, dots: int, dot_char: str = '.') -> None:
        self._write(f"\r{' '*80}\r{prompt}{dot_char*dots}")
        await self._yield_to_event_loop()

    async def get_user_input(self, default_text: str = "", add_newline: bool = True) -> str:
        class NonEmptyValidator(Validator):
            def validate(self, document):
                if not document.text.strip():
                    raise ValidationError(message='', cursor_position=0)

        with self.cursor_control(True):
            if add_newline:
                self._write("\n")

            self._is_edit_mode = bool(default_text)
            try:
                result = await self.prompt_session.prompt_async(
                    FormattedText([('class:prompt','> ')]),
                    default=default_text,
                    validator=NonEmptyValidator(),
                    validate_while_typing=False
                )
                return result.strip()
            finally:
                self._is_edit_mode = False

    async def handle_scroll(self, styled_lines: str, prompt: str, delay: float = 0.5) -> None:
        """Handle scrolling with preserved panel structure."""
        lines = self._handle_text(styled_lines)
        for i in range(len(lines)+1):
            with self.cursor_control(False):
                self._clear_screen()
                for ln in lines[i:]:
                    self._write(ln, newline=True)
                self._write(self.styles.get_format('RESET')+prompt)
                time.sleep(delay)

    async def update_animated_display(self, content: str = "", preserved_msg: str = "", no_spacing: bool = False) -> None:
        """Update the display with animation support."""
        with self.cursor_control(False):
            self._clear_screen()
            if content:
                if preserved_msg:
                    self._write(preserved_msg+("" if no_spacing else "\n\n"))
                self._write(content)
            else:
                self._write(preserved_msg)
            self._write("", 'RESET')