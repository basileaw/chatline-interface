# display/terminal.py

import sys
import shutil
import asyncio
from dataclasses import dataclass
from prompt_toolkit import PromptSession
from prompt_toolkit.validation import Validator, ValidationError
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.key_binding import KeyBindings

@dataclass
class TerminalSize:
    """Terminal dimensions."""
    columns: int
    lines: int

class DisplayTerminal:
    """Terminal ops: screen management, cursor control, and input."""
    def __init__(self):
        """Initialize terminal management."""
        self._cursor_visible = True
        self._is_edit_mode = False
        self._setup_key_bindings()
        
    def _setup_key_bindings(self) -> None:
        """Set up keyboard shortcuts (Ctrl-E: edit, Ctrl-R: retry)."""
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

    @property
    def term_width(self) -> int:
        """Return current terminal width."""
        return self.get_size().columns

    def get_size(self) -> TerminalSize:
        """Return terminal size."""
        size = shutil.get_terminal_size()
        return TerminalSize(columns=size.columns, lines=size.lines)

    def _is_terminal(self) -> bool:
        """Return True if stdout is a terminal."""
        return sys.stdout.isatty()

    def _manage_cursor(self, show: bool) -> None:
        """Toggle cursor visibility."""
        if self._cursor_visible != show and self._is_terminal():
            self._cursor_visible = show
            sys.stdout.write("\033[?25h" if show else "\033[?25l")
            sys.stdout.flush()

    def show_cursor(self) -> None:
        """Show the cursor."""
        self._manage_cursor(True)

    def hide_cursor(self) -> None:
        """Hide the cursor."""
        self._manage_cursor(False)

    def reset(self) -> None:
        """Reset terminal (show cursor and clear screen)."""
        self.show_cursor()
        self.clear_screen()

    def clear_screen(self) -> None:
        """Clear the terminal screen."""
        if self._is_terminal():
            sys.stdout.write("\033[2J\033[H")
            sys.stdout.flush()

    def write(self, text: str = "", newline: bool = False) -> None:
        """Write text to the terminal."""
        self.hide_cursor()
        try:
            sys.stdout.write(text)
            if newline:
                sys.stdout.write('\n')
            sys.stdout.flush()
        finally:
            self.hide_cursor()

    async def get_user_input(self, default_text: str = "", add_newline: bool = True) -> str:
        """Prompt user for input."""
        class NonEmptyValidator(Validator):
            def validate(self, document):
                if not document.text.strip():
                    raise ValidationError(message='', cursor_position=0)

        if add_newline:
            self.write("\n")
        self._is_edit_mode = bool(default_text)
        try:
            self.show_cursor()
            result = await self.prompt_session.prompt_async(
                FormattedText([('class:prompt', '> ')]),
                default=default_text,
                validator=NonEmptyValidator(),
                validate_while_typing=False
            )
            return result.strip()
        finally:
            self._is_edit_mode = False
            self.hide_cursor()

    async def yield_to_event_loop(self) -> None:
        """Yield briefly to the event loop."""
        await asyncio.sleep(0)
