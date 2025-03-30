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
    """Low-level terminal operations and I/O."""
    def __init__(self):
        """Initialize terminal state and key bindings."""
        self._cursor_visible = True
        self._is_edit_mode = False
        self._setup_key_bindings()

    def _setup_key_bindings(self) -> None:
        """Setup key shortcuts: Ctrl-E for edit, Ctrl-R for retry."""
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
    def width(self) -> int:
        """Return terminal width."""
        return self.get_size().columns

    @property
    def height(self) -> int:
        """Return terminal height."""
        return self.get_size().lines

    def get_size(self) -> TerminalSize:
        """Get terminal dimensions."""
        size = shutil.get_terminal_size()
        return TerminalSize(columns=size.columns, lines=size.lines)

    def _is_terminal(self) -> bool:
        """Return True if stdout is a terminal."""
        return sys.stdout.isatty()

    def _manage_cursor(self, show: bool) -> None:
        """Toggle cursor visibility based on 'show' flag."""
        if self._cursor_visible != show and self._is_terminal():
            self._cursor_visible = show
            sys.stdout.write("\033[?25h" if show else "\033[?25l")
            sys.stdout.flush()

    def show_cursor(self) -> None:
        """Make cursor visible and enable blinking."""
        self._manage_cursor(True)
        # if self._is_terminal():
        #     # # Add cursor blinking and set to block style
        #     # sys.stdout.write("\033[?12h")  # Enable cursor blinking
        #     # sys.stdout.write("\033[1 q")   # Set cursor style to blinking block
        #     sys.stdout.flush()

    def hide_cursor(self) -> None:
        """Make cursor hidden."""
        self._manage_cursor(False)

    def reset(self) -> None:
        """Reset terminal: show cursor and clear screen."""
        self.show_cursor()
        self.clear_screen()

    def clear_screen(self) -> None:
        """Clear the terminal screen."""
        if self._is_terminal():
            sys.stdout.write("\033[2J\033[H")
            sys.stdout.flush()

    def write(self, text: str = "", newline: bool = False) -> None:
        """Write text to stdout; append newline if requested."""
        try:
            sys.stdout.write(text)
            if newline:
                sys.stdout.write('\n')
            sys.stdout.flush()
        except IOError:
            pass  # Ignore pipe errors

    def write_line(self, text: str = "") -> None:
        """Write text with newline."""
        self.write(text, newline=True)

    async def get_user_input(
        self, 
        default_text: str = "", 
        add_newline: bool = True,
        hide_cursor: bool = True
    ) -> str:
        """Prompt user for input with default text."""
        class NonEmptyValidator(Validator):
            def validate(self, document):
                if not document.text.strip():
                    raise ValidationError(message='', cursor_position=0)

        if add_newline:
            self.write_line()
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
            if hide_cursor:
                self.hide_cursor()

    def format_prompt(self, text: str) -> str:
        """Format prompt text with proper ending punctuation."""
        end_char = text[-1] if text.endswith(('?', '!')) else '.'
        return f"> {text.rstrip('?.!')}{end_char * 3}"

    async def update_display(
        self,
        content: str = None,
        prompt: str = None,
        preserve_cursor: bool = False
    ) -> None:
        """Clear screen and update display with content and optional prompt."""
        if not preserve_cursor:
            self.hide_cursor()
        self.clear_screen()
        if content:
            self.write(content)
            if prompt:
                self.write('\n')
        if prompt:
            self.write(prompt)
        if not preserve_cursor:
            self.hide_cursor()

    async def yield_to_event_loop(self) -> None:
        """Yield control to the event loop briefly."""
        await asyncio.sleep(0)

    def __enter__(self):
        """Context manager enter: hide cursor."""
        self.hide_cursor()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit: show cursor."""
        self.show_cursor()
