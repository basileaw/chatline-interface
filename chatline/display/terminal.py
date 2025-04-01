# display/terminal.py
import sys
import shutil
import asyncio
import termios
import tty
import fcntl
import os
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
        # Use a visually distinct prompt separator that makes it clear where user input begins
        self._prompt_prefix = "> "
        self._prompt_separator = ""  # Visual separator between prompt and input area
        # ANSI escape codes for text formatting
        self._reset_style = "\033[0m"  # Reset all attributes
        self._default_style = "\033[0;37m"  # Default white text
        # Screen buffer for smoother rendering
        self._current_buffer = ""
        self._last_size = self.get_size()

    async def pre_initialize_prompt_toolkit(self):
        """
        Silently pre-initialize prompt toolkit components without showing the cursor.
        """
        try:
            # Save the original stdout
            original_stdout = sys.stdout
            
            # First, ensure cursor is hidden before we do anything
            self._cursor_visible = False
            sys.stdout.write("\033[?25l")  # Hide cursor
            sys.stdout.flush()
            
            # Redirect stdout to /dev/null (or NUL on Windows)
            null_device = open(os.devnull, 'w')
            sys.stdout = null_device
            
            # Create a temporary PromptSession with the same configuration
            # but isolated from our main session
            temp_kb = KeyBindings()
            temp_session = PromptSession(key_bindings=temp_kb, complete_while_typing=False)
            
            try:
                # Create a background task that will cancel the prompt after a brief delay
                async def cancel_after_delay(task):
                    await asyncio.sleep(0.0)
                    task.cancel()
                
                # Start the temporary prompt session
                prompt_task = asyncio.create_task(
                    temp_session.prompt_async(
                        message="",
                        default="",
                        validate_while_typing=False
                    )
                )
                
                # Create cancellation task
                cancel_task = asyncio.create_task(cancel_after_delay(prompt_task))
                
                # Wait for either completion or cancellation
                await asyncio.gather(prompt_task, cancel_task, return_exceptions=True)
                
            except (asyncio.CancelledError, Exception):
                # Expected - we're forcing cancellation
                pass
            
        except Exception as e:
            pass
        finally:
            # Restore the original stdout
            if 'original_stdout' in locals():
                sys.stdout = original_stdout
                
            # Close the null device if it was opened
            if 'null_device' in locals():
                null_device.close()
            
            # Ensure cursor remains hidden after restoration
            self._cursor_visible = False
            sys.stdout.write("\033[?25l")  # Hide cursor again
            sys.stdout.flush()
                
            # Also clear the screen after stdout is restored
            sys.stdout.write("\033[2J\033[H")  # Clear and home
            sys.stdout.flush()

    class NonEmptyValidator(Validator):
        def validate(self, document):
            if not document.text.strip():
                raise ValidationError(message='', cursor_position=0)

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
        """Make cursor visible and restore previous style."""
        self._manage_cursor(True)  # Always send cursor style commands
        sys.stdout.write("\033[?12h")  # Enable cursor blinking
        sys.stdout.write("\033[1 q")    # Set cursor style to blinking block
        sys.stdout.flush()

    def hide_cursor(self) -> None:
        """Make cursor hidden, preserving its style for next show_cursor()."""
        if self._cursor_visible:
            # Store info that cursor was blinking before hiding
            self._was_blinking = True
            # Standard hide cursor sequence
            self._cursor_visible = False
            sys.stdout.write("\033[?25l")
            sys.stdout.flush()

    def reset(self) -> None:
        """Reset terminal: show cursor and clear screen."""
        self.show_cursor()
        self.clear_screen()

    def clear_screen(self) -> None:
        """Clear the terminal screen and reset cursor position."""
        if self._is_terminal():
            # More efficient clearing approach - clear and home in one operation
            sys.stdout.write("\033[2J\033[H")
            sys.stdout.flush()
        self._current_buffer = ""

    def write(self, text: str = "", newline: bool = False) -> None:
        """Write text to stdout; append newline if requested."""
        try:
            sys.stdout.write(text)
            if newline:
                sys.stdout.write('\n')
            sys.stdout.flush()
            # Update our buffer with the content
            self._current_buffer += text
            if newline:
                self._current_buffer += '\n'
        except IOError:
            pass  # Ignore pipe errors

    def write_line(self, text: str = "") -> None:
        """Write text with newline."""
        self.write(text, newline=True)

    def _read_line_raw(self):
        """
        Read a line of input in raw mode with full keyboard shortcut support and arrow key navigation.
        """
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            # Reset text attributes and apply default style before displaying prompt
            styled_prompt = f"{self._reset_style}{self._default_style}{self._prompt_prefix}{self._prompt_separator}"
            prompt_len = len(self._prompt_prefix) + len(self._prompt_separator)
            self.write(styled_prompt)
            self.show_cursor()
            # Switch to raw mode
            tty.setraw(fd, termios.TCSANOW)
            input_chars = []
            cursor_pos = 0  # Position in the input buffer (0 = start)
            while True:
                c = os.read(fd, 1)
                # Handle special control sequences
                if c == b'\x05':  # Ctrl+E
                    self.write("\r\n")
                    self.hide_cursor()  # Hide immediately on command
                    return "edit"
                elif c == b'\x12':  # Ctrl+R
                    self.write("\r\n")
                    self.hide_cursor()  # Hide immediately on command
                    return "retry"
                elif c == b'\x03':  # Ctrl+C
                    self.write("^C\r\n")
                    self.hide_cursor()  # Hide immediately on interrupt
                    raise KeyboardInterrupt()
                elif c == b'\x04':  # Ctrl+D
                    if not input_chars:
                        self.write("\r\n")
                        self.hide_cursor()  # Hide immediately on exit
                        return "exit"
                # Handle standard terminal editing functions
                elif c in (b'\r', b'\n'):  # Enter
                    self.write("\r\n")
                    self.hide_cursor()  # Hide cursor IMMEDIATELY when Enter is pressed
                    break
                elif c == b'\x7f':  # Backspace
                    if cursor_pos > 0:  # Only if cursor isn't at beginning
                        # Remove the character at cursor_pos - 1
                        input_chars.pop(cursor_pos - 1)
                        cursor_pos -= 1
                        # Redraw the line with consistent styling
                        self.write("\r" + styled_prompt + "".join(input_chars) + " " + "\b")
                        # Move cursor back to correct position
                        if cursor_pos < len(input_chars):
                            self.write("\033[" + str(len(input_chars) - cursor_pos) + "D")
                elif c == b'\x1b':  # Escape sequence
                    seq = os.read(fd, 1)
                    if seq == b'[':  # CSI sequence
                        code = os.read(fd, 1)
                        if code == b'A':  # Up arrow - history (not implemented)
                            pass
                        elif code == b'B':  # Down arrow - history (not implemented)
                            pass
                        elif code == b'C':  # Right arrow - move cursor right
                            if cursor_pos < len(input_chars):
                                cursor_pos += 1
                                self.write("\033[C")  # Move cursor right
                        elif code == b'D':  # Left arrow - move cursor left
                            if cursor_pos > 0:
                                cursor_pos -= 1
                                self.write("\033[D")  # Move cursor left
                        elif code == b'H':  # Home - move to beginning
                            self.write("\r" + styled_prompt)
                            cursor_pos = 0
                        elif code == b'F':  # End - move to end
                            # Move to end of line
                            if cursor_pos < len(input_chars):
                                self.write("\033[" + str(len(input_chars) - cursor_pos) + "C")
                                cursor_pos = len(input_chars)
                        elif code == b'3' and os.read(fd, 1) == b'~':  # Handle delete key
                            if cursor_pos < len(input_chars):
                                # Remove character at cursor position
                                input_chars.pop(cursor_pos)
                                # Redraw from cursor to end
                                self.write("".join(input_chars[cursor_pos:]) + " " + "\b")
                                # Move cursor back to correct position
                                if cursor_pos < len(input_chars):
                                    self.write("\033[" + str(len(input_chars) - cursor_pos) + "D")
                # Regular characters - insert at cursor position
                elif ord(c) >= 32:  # Printable characters
                    char = c.decode('utf-8')
                    input_chars.insert(cursor_pos, char)
                    cursor_pos += 1
                    # Redraw from cursor to end with consistent styling
                    self.write(char + "".join(input_chars[cursor_pos:]))
                    # Move cursor back to correct position if needed
                    if cursor_pos < len(input_chars):
                        self.write("\033[" + str(len(input_chars) - cursor_pos) + "D")
            return ''.join(input_chars)
        finally:
            # Restore terminal settings
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            # Reset styling before exiting
            self.write(self._reset_style)
            self.hide_cursor()  # Always hide cursor when done with input

    async def get_user_input(
        self,
        default_text: str = "",
        add_newline: bool = True,
        hide_cursor: bool = True
    ) -> str:
        """
        Hybrid input system that preserves cursor blinking in normal mode.
        For edit mode (default_text is provided): Uses prompt_toolkit's full capabilities.
        For normal input: Uses raw mode with custom input handling for shortcuts.

        Args:
            default_text: Pre-filled text for edit mode
            add_newline: Whether to add a newline before prompt
            hide_cursor: Whether to hide cursor after input

        Returns:
            User input string (without prompt)
        """
        if add_newline:
            self.write_line()
        self._is_edit_mode = bool(default_text)
        try:
            if default_text:
                # Reset styling before prompt
                self.write(self._reset_style + self._default_style)
                # For edit mode: Use full prompt_toolkit capabilities
                self.show_cursor()
                result = await self.prompt_session.prompt_async(
                    FormattedText([('class:prompt', f"{self._prompt_prefix}{self._prompt_separator}")]),
                    default=default_text,
                    validator=self.NonEmptyValidator(),
                    validate_while_typing=False
                )
                # Hide cursor IMMEDIATELY after input is received, before any processing
                if hide_cursor:
                    self.hide_cursor()
                return result.strip()
            else:
                # For standard input, use our custom raw mode handling
                result = await asyncio.get_event_loop().run_in_executor(
                    None, self._read_line_raw
                )
                # Hide cursor is now handled directly in _read_line_raw
                # Check for special commands
                if result in ['edit', 'retry', 'exit']:
                    return result
                # Handle empty input validation
                while not result.strip():
                    self.write_line()
                    result = await asyncio.get_event_loop().run_in_executor(
                        None, self._read_line_raw
                    )
                    if result in ['edit', 'retry', 'exit']:
                        return result
                return result.strip()
        finally:
            # Reset styling before exiting
            self.write(self._reset_style)
            self._is_edit_mode = False
            if hide_cursor:
                self.hide_cursor()  # Ensure cursor is hidden even if an exception occurs

    def format_prompt(self, text: str) -> str:
        """Format prompt text with proper ending punctuation."""
        end_char = text[-1] if text.endswith(('?', '!')) else '.'
        # Apply consistent styling to formatted prompts
        return f"{self._reset_style}{self._default_style}{self._prompt_prefix}{text.rstrip('?.!')}{end_char * 3}"

    def _prepare_display_update(self, content: str = None, prompt: str = None) -> str:
        """Prepare display update content without actually writing to terminal."""
        buffer = ""
        if content:
            # Apply reset before content to ensure consistent style
            buffer += self._reset_style + content
        if prompt:
            buffer += '\n'
        if prompt:
            # Prompt already includes reset styling from format_prompt
            buffer += prompt
        return buffer

    async def update_display(
        self,
        content: str = None,
        prompt: str = None,
        preserve_cursor: bool = False
    ) -> None:
        """
        Clear screen and update display with content and optional prompt.
        Uses double-buffering approach to minimize flicker.
        """
        # Hide cursor during update, unless specified otherwise
        if not preserve_cursor:
            self.hide_cursor()
        # Prepare next screen buffer
        new_buffer = self._prepare_display_update(content, prompt)
        # Check if terminal size changed
        current_size = self.get_size()
        if current_size.columns != self._last_size.columns or current_size.lines != self._last_size.lines:
            # Terminal size changed, do a full clear
            self.clear_screen()
            self._last_size = current_size
        else:
            # Just move cursor to home position
            sys.stdout.write("\033[H")
        # Write the buffer directly
        sys.stdout.write(new_buffer)
        # Clear any remaining content from previous display
        # This uses ED (Erase in Display) with parameter 0 to clear from cursor to end of screen
        sys.stdout.write("\033[0J")
        sys.stdout.flush()
        # Update our current buffer
        self._current_buffer = new_buffer
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
