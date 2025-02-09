# display/terminal.py

import sys
import shutil
import asyncio
from dataclasses import dataclass
from typing import Optional, Tuple
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
    """
    Handles core terminal operations including screen management,
    cursor control, and user input handling.
    
    This class encapsulates all direct terminal interaction, providing
    a clean interface for other components to use.
    """
    def __init__(self):
        """Initialize terminal management."""
        self._cursor_visible = True
        self._is_edit_mode = False
        self._setup_key_bindings()
        
    def _setup_key_bindings(self) -> None:
        """Configure keyboard shortcuts."""
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

        self.prompt_session = PromptSession(
            key_bindings=kb,
            complete_while_typing=False
        )

    @property
    def term_width(self) -> int:
        """Get current terminal width."""
        return self.get_size().columns

    def get_size(self) -> TerminalSize:
        """Get current terminal dimensions."""
        size = shutil.get_terminal_size()
        return TerminalSize(columns=size.columns, lines=size.lines)

    def _is_terminal(self) -> bool:
        """Check if output is going to a terminal."""
        return sys.stdout.isatty()

    def _manage_cursor(self, show: bool) -> None:
        """Manage cursor visibility."""
        if self._cursor_visible != show and self._is_terminal():
            self._cursor_visible = show
            sys.stdout.write("\033[?25h" if show else "\033[?25l")
            sys.stdout.flush()

    def show_cursor(self) -> None:
        """Make cursor visible."""
        self._manage_cursor(True)

    def hide_cursor(self) -> None:
        """Hide cursor."""
        self._manage_cursor(False)

    def reset(self) -> None:
        """Reset terminal state."""
        self.show_cursor()
        self.clear_screen()

    def clear_screen(self) -> None:
        """Clear terminal screen."""
        if self._is_terminal():
            sys.stdout.write("\033[2J\033[H")
            sys.stdout.flush()

    def write(self, text: str = "", newline: bool = False) -> None:
        """
        Write text to terminal.
        
        Args:
            text: Text to write
            newline: Whether to append newline
        """
        self.hide_cursor()
        try:
            sys.stdout.write(text)
            if newline:
                sys.stdout.write('\n')
            sys.stdout.flush()
        finally:
            self.hide_cursor()

    async def get_user_input(
        self,
        default_text: str = "",
        add_newline: bool = True
    ) -> str:
        """
        Get input from user with proper terminal handling.
        
        Args:
            default_text: Initial text in input
            add_newline: Whether to add newline before prompt
            
        Returns:
            User input string
        """
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
        """Yield control to event loop briefly."""
        await asyncio.sleep(0)