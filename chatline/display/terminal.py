# display/terminal.py
import sys
import shutil
import asyncio
import termios
import tty
import fcntl
import os
from dataclasses import dataclass
from typing import Optional

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

        # Selection styling - can be customized per terminal
        # Default: matches common cursor highlighting
        self._selection_style = self._detect_selection_style()

        # Detect if we're in a web terminal for optimizations
        self._is_web_terminal = self._detect_web_terminal()

    def _detect_web_terminal(self):
        """Detect if running in a web-based terminal."""
        # Check for common web terminal indicators
        term = os.environ.get("TERM", "")
        # Check for ttyd, xterm.js, or other web terminal indicators
        web_indicators = ["xterm-256color", "xterm-color"]
        is_web = term in web_indicators

        # Also check for specific environment variables that web terminals might set
        if os.environ.get("TERMINAIDE", ""):
            is_web = True

        return is_web

    def set_web_terminal_mode(self, enabled: bool = True):
        """
        Enable or disable web terminal optimizations.

        Args:
            enabled: Whether to enable web terminal mode
        """
        self._is_web_terminal = enabled

    def _detect_selection_style(self):
        """Detect the best selection style for the current terminal."""
        term = os.environ.get("TERM", "")
        colorterm = os.environ.get("COLORTERM", "")

        # For modern terminals with true color support
        if "truecolor" in colorterm or "24bit" in colorterm:
            # Use a blue selection similar to many modern terminals
            return {
                "start": "\033[48;2;82;139;255m\033[38;2;255;255;255m",
                "end": "\033[0m",
            }
        # For 256 color terminals
        elif "256" in term:
            # Use white bg/black fg for dark terminals, or blue bg/white fg
            return {
                "start": "\033[48;5;67m\033[38;5;255m",  # Blue bg, white fg
                "end": "\033[0m",
            }
        else:
            # Fallback to reverse video
            return {"start": "\033[7m", "end": "\033[27m"}

    def set_selection_style(self, bg_color=None, fg_color=None):
        """
        Manually set selection colors to match your terminal's cursor.

        Args:
            bg_color: Background color (e.g., '48;5;255' for 256-color white,
                     '48;2;82;139;255' for RGB blue)
            fg_color: Foreground color (e.g., '38;5;232' for 256-color black)
        """
        if bg_color and fg_color:
            self._selection_style = {
                "start": f"\033[{bg_color}m\033[{fg_color}m",
                "end": "\033[0m",
            }
        elif bg_color:
            self._selection_style = {"start": f"\033[{bg_color}m", "end": "\033[0m"}

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
            null_device = open(os.devnull, "w")
            sys.stdout = null_device

            # Create a temporary PromptSession with the same configuration
            # but isolated from our main session
            temp_kb = KeyBindings()
            temp_session = PromptSession(
                key_bindings=temp_kb, complete_while_typing=False
            )

            try:
                # Create a background task that will cancel the prompt after a brief delay
                async def cancel_after_delay(task):
                    await asyncio.sleep(0.0)
                    task.cancel()

                # Start the temporary prompt session
                prompt_task = asyncio.create_task(
                    temp_session.prompt_async(
                        message="", default="", validate_while_typing=False
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
            if "original_stdout" in locals():
                sys.stdout = original_stdout

            # Close the null device if it was opened
            if "null_device" in locals():
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
                raise ValidationError(message="", cursor_position=0)

    def _setup_key_bindings(self) -> None:
        """Setup key shortcuts: Ctrl-E for edit, Ctrl-R for retry."""
        kb = KeyBindings()

        @kb.add("c-e")
        def _(event):
            if not self._is_edit_mode:
                event.current_buffer.text = "edit"
                event.app.exit(result=event.current_buffer.text)

        @kb.add("c-r")
        def _(event):
            if not self._is_edit_mode:
                event.current_buffer.text = "retry"
                event.app.exit(result=event.current_buffer.text)

        self.prompt_session = PromptSession(
            key_bindings=kb, complete_while_typing=False
        )

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
        sys.stdout.write("\033[1 q")  # Set cursor style to blinking block
        sys.stdout.flush()

    def hide_cursor(self) -> None:
        """Make cursor hidden, preserving its style for next show_cursor()."""
        if self._cursor_visible:
            # Store info that cursor was blinking before hiding
            self._was_blinking = True
            # Standard hide cursor sequence
            self._cursor_visible = False
            # For web terminals, ensure the hide command is sent with high priority
            if self._is_web_terminal:
                # Force immediate hiding with multiple methods
                sys.stdout.write("\033[?25l\033[?1c")
            else:
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
                sys.stdout.write("\n")
            sys.stdout.flush()
            # Update our buffer with the content
            self._current_buffer += text
            if newline:
                self._current_buffer += "\n"
        except IOError:
            pass  # Ignore pipe errors

    def write_line(self, text: str = "") -> None:
        """Write text with newline."""
        self.write(text, newline=True)

    def _calculate_line_count(self, text: str, prompt_len: int) -> int:
        """Calculate how many lines the text will occupy in the terminal."""
        if not text:
            return 1

        total_length = prompt_len + len(text)
        term_width = self.get_size().columns

        # First line has the prompt taking up space
        first_line_chars = term_width - prompt_len

        if total_length <= term_width:
            return 1

        # Calculate remaining lines after first line
        remaining_chars = max(0, total_length - first_line_chars)
        additional_lines = (remaining_chars + term_width - 1) // term_width

        return 1 + additional_lines

    def _read_line_raw(
        self,
        prompt_prefix: Optional[str] = None,
        prompt_separator: Optional[str] = None,
    ):
        """
        Read a line of input in raw mode with full keyboard shortcut support and arrow key navigation.
        Now with Unicode support, better escape sequence handling, and improved multi-line editing.
        """
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)

        # For reading UTF-8 characters
        utf8_buffer = bytearray()

        def read_utf8_char():
            """Read a complete UTF-8 character from input."""
            # Read first byte
            first_byte = os.read(fd, 1)
            if not first_byte:
                return None

            # Check if it's ASCII (0xxxxxxx)
            if first_byte[0] & 0x80 == 0:
                return first_byte

            # Determine number of bytes in UTF-8 sequence
            if first_byte[0] & 0xE0 == 0xC0:  # 110xxxxx - 2 bytes
                num_bytes = 2
            elif first_byte[0] & 0xF0 == 0xE0:  # 1110xxxx - 3 bytes
                num_bytes = 3
            elif first_byte[0] & 0xF8 == 0xF0:  # 11110xxx - 4 bytes
                num_bytes = 4
            else:
                # Invalid UTF-8 start byte, return as-is
                return first_byte

            # Read remaining bytes
            result = first_byte
            for _ in range(num_bytes - 1):
                next_byte = os.read(fd, 1)
                if not next_byte or (next_byte[0] & 0xC0) != 0x80:
                    # Invalid continuation byte
                    return first_byte  # Return just the first byte
                result += next_byte

            return result

        def read_escape_sequence():
            """Read and parse a complete escape sequence."""
            seq = os.read(fd, 1)
            if seq != b"[":
                return b"\x1b" + seq  # Not a CSI sequence

            # Read the rest of the sequence
            chars = b"["
            while True:
                c = os.read(fd, 1)
                if not c:
                    break
                chars += c
                # Check if we've reached the end of the sequence
                if c[0] >= 0x40 and c[0] <= 0x7E:  # @ through ~
                    break

            return b"\x1b" + chars

        def get_display_width(text: str) -> int:
            """Get the display width of text, accounting for wide characters."""
            # This is a simplified version - ideally would use wcwidth
            width = 0
            for char in text:
                # Simple heuristic: CJK characters are width 2
                if (
                    "\u4e00" <= char <= "\u9fff"
                    or "\u3040" <= char <= "\u309f"
                    or "\u30a0" <= char <= "\u30ff"
                ):
                    width += 2
                else:
                    width += 1
            return width

        def redraw_input(
            input_chars, cursor_pos, styled_prompt, prompt_len, selection_start=None
        ):
            """Redraw the entire input, handling multi-line properly with optimized rendering."""
            current_input = "".join(input_chars)

            # Calculate line information
            total_chars = prompt_len + get_display_width(current_input[:cursor_pos])
            cursor_line = total_chars // self.width
            cursor_col = total_chars % self.width

            # Calculate total lines needed
            total_lines = self._calculate_line_count(current_input, prompt_len)

            # Build the entire output in a single buffer to minimize flashing
            output_buffer = []

            # Move to start of input area
            output_buffer.append("\r")
            if cursor_line > 0:
                output_buffer.append(f"\033[{cursor_line}A")

            # Clear from cursor position to end of screen (more efficient than line-by-line)
            output_buffer.append("\033[0J")

            # Write the prompt
            output_buffer.append(styled_prompt)

            # Write the content with selection highlighting
            if selection_start is not None and selection_start != cursor_pos:
                # Determine selection bounds
                sel_start = min(selection_start, cursor_pos)
                sel_end = max(selection_start, cursor_pos)

                # Write text in three parts: before selection, selection, after selection
                before = "".join(input_chars[:sel_start])
                selected = "".join(input_chars[sel_start:sel_end])
                after = "".join(input_chars[sel_end:])

                output_buffer.append(before)
                # Use the terminal's selection style
                output_buffer.append(
                    self._selection_style["start"]
                    + selected
                    + self._selection_style["end"]
                )
                output_buffer.append(after)
            else:
                # No selection, write normally
                output_buffer.append(current_input)

            # Calculate final cursor position
            if cursor_pos < len(input_chars):
                # Calculate where cursor should be
                chars_to_cursor = prompt_len + get_display_width(
                    current_input[:cursor_pos]
                )
                target_line = chars_to_cursor // self.width
                target_col = chars_to_cursor % self.width

                # Calculate relative movement from end of text
                chars_after_cursor = get_display_width(current_input[cursor_pos:])
                if chars_after_cursor > 0:
                    # Move back from end of text
                    output_buffer.append(f"\033[{chars_after_cursor}D")

                # Additional positioning if we need to go up lines
                current_end_line = (
                    prompt_len + get_display_width(current_input)
                ) // self.width
                if target_line < current_end_line:
                    lines_up = current_end_line - target_line
                    output_buffer.append(f"\033[{lines_up}A")
                    # Adjust horizontal position
                    output_buffer.append(f"\r\033[{target_col}C")

            # Write everything in a single operation
            self.write("".join(output_buffer))

        def optimized_char_insert(
            input_chars, cursor_pos, char, styled_prompt, prompt_len
        ):
            """Optimized character insertion for single-line cases."""
            # For simple single-line cases, just insert the character without full redraw
            remaining_text = "".join(input_chars[cursor_pos:])

            # Build output in single buffer
            output = [char]
            if remaining_text:
                output.append(remaining_text)
                output.append(f"\033[{len(remaining_text)}D")

            self.write("".join(output))

        def get_selected_text(input_chars, selection_start, cursor_pos):
            """Get the currently selected text."""
            if selection_start is None:
                return ""
            start = min(selection_start, cursor_pos)
            end = max(selection_start, cursor_pos)
            return "".join(input_chars[start:end])

        def delete_selection(input_chars, selection_start, cursor_pos):
            """Delete selected text and return new cursor position."""
            if selection_start is None:
                return input_chars, cursor_pos

            start = min(selection_start, cursor_pos)
            end = max(selection_start, cursor_pos)

            # Remove selected characters
            new_chars = input_chars[:start] + input_chars[end:]
            return new_chars, start

        try:
            # Use provided prompt components or fall back to instance variables
            current_prefix = (
                prompt_prefix if prompt_prefix is not None else self._prompt_prefix
            )
            current_separator = (
                prompt_separator
                if prompt_separator is not None
                else self._prompt_separator
            )

            # Reset text attributes and apply default style before displaying prompt
            styled_prompt = f"{self._reset_style}{self._default_style}{current_prefix}{current_separator}"
            prompt_len = len(current_prefix) + len(current_separator)
            self.write(styled_prompt)
            self.show_cursor()

            # Switch to raw mode
            tty.setraw(fd, termios.TCSANOW)
            input_chars = []
            cursor_pos = 0  # Position in the input buffer (0 = start)
            selection_start = None  # Start of selection (None = no selection)

            while True:
                c = read_utf8_char()
                if not c:
                    continue

                # Handle special control sequences
                if c == b"\x05":  # Ctrl+E
                    self.write("\r\n")
                    self.hide_cursor()
                    return "edit"
                elif c == b"\x12":  # Ctrl+R
                    self.write("\r\n")
                    self.hide_cursor()
                    return "retry"
                elif c == b"\x10":  # Ctrl+P
                    # Only work if input buffer is empty
                    if not input_chars:
                        continue_text = "[CONTINUE]"
                        self.write(continue_text)
                        input_chars = list(continue_text)
                        cursor_pos = len(input_chars)
                        self.write("\r\n")
                        self.hide_cursor()
                        return "".join(input_chars)
                elif c == b"\x03":  # Ctrl+C
                    self.write("^C\r\n")
                    self.hide_cursor()
                    raise KeyboardInterrupt()
                elif c == b"\x04":  # Ctrl+D
                    if not input_chars:
                        self.write("\r\n")
                        self.hide_cursor()
                        return "exit"
                elif c in (b"\r", b"\n"):  # Enter
                    self.write("\r\n")
                    self.hide_cursor()
                    break
                elif c == b"\x7f":  # Backspace
                    if selection_start is not None and selection_start != cursor_pos:
                        # Delete selection
                        input_chars, cursor_pos = delete_selection(
                            input_chars, selection_start, cursor_pos
                        )
                        selection_start = None
                        redraw_input(input_chars, cursor_pos, styled_prompt, prompt_len)
                    elif cursor_pos > 0:
                        input_chars.pop(cursor_pos - 1)
                        cursor_pos -= 1
                        redraw_input(input_chars, cursor_pos, styled_prompt, prompt_len)
                elif c == b"\x1b":  # Escape sequence
                    seq = read_escape_sequence()

                    # Parse common sequences
                    if seq == b"\x1b[A":  # Up arrow
                        pass  # History not implemented
                    elif seq == b"\x1b[B":  # Down arrow
                        pass  # History not implemented
                    elif seq == b"\x1b[C":  # Right arrow
                        if cursor_pos < len(input_chars):
                            cursor_pos += 1
                            selection_start = None  # Clear selection
                            # For web terminals or multi-line text, do full redraw
                            # Otherwise, just move cursor
                            if (
                                self._is_web_terminal
                                or (prompt_len + len("".join(input_chars))) > self.width
                            ):
                                redraw_input(
                                    input_chars, cursor_pos, styled_prompt, prompt_len
                                )
                            else:
                                self.write("\033[C")
                    elif seq == b"\x1b[D":  # Left arrow
                        if cursor_pos > 0:
                            cursor_pos -= 1
                            selection_start = None  # Clear selection
                            # For web terminals or multi-line text, do full redraw
                            # Otherwise, just move cursor
                            if (
                                self._is_web_terminal
                                or (prompt_len + len("".join(input_chars))) > self.width
                            ):
                                redraw_input(
                                    input_chars, cursor_pos, styled_prompt, prompt_len
                                )
                            else:
                                self.write("\033[D")
                    elif seq == b"\x1b[1;2C":  # Shift+Right arrow
                        if cursor_pos < len(input_chars):
                            if selection_start is None:
                                selection_start = cursor_pos
                            cursor_pos += 1
                            redraw_input(
                                input_chars,
                                cursor_pos,
                                styled_prompt,
                                prompt_len,
                                selection_start,
                            )
                    elif seq == b"\x1b[1;2D":  # Shift+Left arrow
                        if cursor_pos > 0:
                            if selection_start is None:
                                selection_start = cursor_pos
                            cursor_pos -= 1
                            redraw_input(
                                input_chars,
                                cursor_pos,
                                styled_prompt,
                                prompt_len,
                                selection_start,
                            )
                    elif seq == b"\x1b[1;2H":  # Shift+Home - select to beginning
                        if cursor_pos > 0:
                            if selection_start is None:
                                selection_start = cursor_pos
                            cursor_pos = 0
                            redraw_input(
                                input_chars,
                                cursor_pos,
                                styled_prompt,
                                prompt_len,
                                selection_start,
                            )
                    elif seq == b"\x1b[1;2F":  # Shift+End - select to end
                        if cursor_pos < len(input_chars):
                            if selection_start is None:
                                selection_start = cursor_pos
                            cursor_pos = len(input_chars)
                            redraw_input(
                                input_chars,
                                cursor_pos,
                                styled_prompt,
                                prompt_len,
                                selection_start,
                            )
                    elif seq == b"\x1b[H" or seq == b"\x1b[1~":  # Home
                        if cursor_pos > 0:
                            cursor_pos = 0
                            selection_start = None  # Clear selection
                            redraw_input(
                                input_chars, cursor_pos, styled_prompt, prompt_len
                            )
                    elif seq == b"\x1b[F" or seq == b"\x1b[4~":  # End
                        if cursor_pos < len(input_chars):
                            cursor_pos = len(input_chars)
                            selection_start = None  # Clear selection
                            redraw_input(
                                input_chars, cursor_pos, styled_prompt, prompt_len
                            )
                    elif seq == b"\x1b[3~":  # Delete
                        if (
                            selection_start is not None
                            and selection_start != cursor_pos
                        ):
                            # Delete selection
                            input_chars, cursor_pos = delete_selection(
                                input_chars, selection_start, cursor_pos
                            )
                            selection_start = None
                            redraw_input(
                                input_chars, cursor_pos, styled_prompt, prompt_len
                            )
                        elif cursor_pos < len(input_chars):
                            input_chars.pop(cursor_pos)
                            redraw_input(
                                input_chars, cursor_pos, styled_prompt, prompt_len
                            )
                    elif seq == b"\x1b[1;5C":  # Ctrl+Right (word forward)
                        # Move to next word boundary
                        while (
                            cursor_pos < len(input_chars)
                            and not input_chars[cursor_pos].isspace()
                        ):
                            cursor_pos += 1
                        while (
                            cursor_pos < len(input_chars)
                            and input_chars[cursor_pos].isspace()
                        ):
                            cursor_pos += 1
                        selection_start = None  # Clear selection
                        redraw_input(input_chars, cursor_pos, styled_prompt, prompt_len)
                    elif seq == b"\x1b[1;5D":  # Ctrl+Left (word backward)
                        # Move to previous word boundary
                        while cursor_pos > 0 and input_chars[cursor_pos - 1].isspace():
                            cursor_pos -= 1
                        while (
                            cursor_pos > 0 and not input_chars[cursor_pos - 1].isspace()
                        ):
                            cursor_pos -= 1
                        selection_start = None  # Clear selection
                        redraw_input(input_chars, cursor_pos, styled_prompt, prompt_len)
                    elif seq == b"\x1b[1;6C":  # Ctrl+Shift+Right (select word forward)
                        if selection_start is None:
                            selection_start = cursor_pos
                        # Move to next word boundary
                        while (
                            cursor_pos < len(input_chars)
                            and not input_chars[cursor_pos].isspace()
                        ):
                            cursor_pos += 1
                        while (
                            cursor_pos < len(input_chars)
                            and input_chars[cursor_pos].isspace()
                        ):
                            cursor_pos += 1
                        redraw_input(
                            input_chars,
                            cursor_pos,
                            styled_prompt,
                            prompt_len,
                            selection_start,
                        )
                    elif seq == b"\x1b[1;6D":  # Ctrl+Shift+Left (select word backward)
                        if selection_start is None:
                            selection_start = cursor_pos
                        # Move to previous word boundary
                        while cursor_pos > 0 and input_chars[cursor_pos - 1].isspace():
                            cursor_pos -= 1
                        while (
                            cursor_pos > 0 and not input_chars[cursor_pos - 1].isspace()
                        ):
                            cursor_pos -= 1
                        redraw_input(
                            input_chars,
                            cursor_pos,
                            styled_prompt,
                            prompt_len,
                            selection_start,
                        )
                    elif seq == b"\x1b[1;2A":  # Shift+Up - select to beginning
                        if cursor_pos > 0:
                            if selection_start is None:
                                selection_start = cursor_pos
                            cursor_pos = 0
                            redraw_input(
                                input_chars,
                                cursor_pos,
                                styled_prompt,
                                prompt_len,
                                selection_start,
                            )
                    elif seq == b"\x1b[1;2B":  # Shift+Down - select to end
                        if cursor_pos < len(input_chars):
                            if selection_start is None:
                                selection_start = cursor_pos
                            cursor_pos = len(input_chars)
                            redraw_input(
                                input_chars,
                                cursor_pos,
                                styled_prompt,
                                prompt_len,
                                selection_start,
                            )
                else:
                    # Regular character input
                    try:
                        char = c.decode("utf-8")
                        # Handle Ctrl+A (select all)
                        if c == b"\x01":  # Ctrl+A
                            if len(input_chars) > 0:
                                selection_start = 0
                                cursor_pos = len(input_chars)
                                redraw_input(
                                    input_chars,
                                    cursor_pos,
                                    styled_prompt,
                                    prompt_len,
                                    selection_start,
                                )
                        # Handle Ctrl+X (cut)
                        elif c == b"\x18":  # Ctrl+X
                            if (
                                selection_start is not None
                                and selection_start != cursor_pos
                            ):
                                # Note: In a real implementation, you'd copy to clipboard here
                                # For now, just delete the selection
                                input_chars, cursor_pos = delete_selection(
                                    input_chars, selection_start, cursor_pos
                                )
                                selection_start = None
                                redraw_input(
                                    input_chars, cursor_pos, styled_prompt, prompt_len
                                )
                        # Filter out control characters except tab
                        elif ord(char) >= 32 or char == "\t":
                            # If there's a selection, delete it first
                            if (
                                selection_start is not None
                                and selection_start != cursor_pos
                            ):
                                input_chars, cursor_pos = delete_selection(
                                    input_chars, selection_start, cursor_pos
                                )
                                selection_start = None

                            input_chars.insert(cursor_pos, char)
                            cursor_pos += 1

                            # For single-line cases without selection, use optimized insertion
                            current_text = "".join(input_chars)
                            if (
                                len(current_text) + prompt_len <= self.width
                                and selection_start is None
                                and not self._is_web_terminal
                            ):
                                # Use optimized character insertion
                                optimized_char_insert(
                                    input_chars,
                                    cursor_pos - 1,
                                    char,
                                    styled_prompt,
                                    prompt_len,
                                )
                            else:
                                # For multi-line or web terminal, use full redraw
                                redraw_input(
                                    input_chars, cursor_pos, styled_prompt, prompt_len
                                )
                    except UnicodeDecodeError:
                        # Skip invalid UTF-8 sequences
                        pass

            return "".join(input_chars)

        finally:
            # Restore terminal settings
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            # Reset styling before exiting
            self.write(self._reset_style)
            self.hide_cursor()

    async def get_user_input(
        self,
        default_text: str = "",
        add_newline: bool = True,
        hide_cursor: bool = True,
        prompt_prefix: Optional[str] = None,
        prompt_separator: Optional[str] = None,
    ) -> str:
        """
        Hybrid input system that preserves cursor blinking in normal mode.
        For edit mode (default_text is provided): Uses prompt_toolkit's full capabilities.
        For normal input: Uses raw mode with custom input handling for shortcuts.

        Args:
            default_text: Pre-filled text for edit mode
            add_newline: Whether to add a newline before prompt
            hide_cursor: Whether to hide cursor after input
            prompt_prefix: Optional temporary prompt prefix override
            prompt_separator: Optional temporary prompt separator override

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

                # Use provided prompt components or fall back to instance variables
                current_prefix = (
                    prompt_prefix if prompt_prefix is not None else self._prompt_prefix
                )
                current_separator = (
                    prompt_separator
                    if prompt_separator is not None
                    else self._prompt_separator
                )

                result = await self.prompt_session.prompt_async(
                    FormattedText(
                        [
                            (
                                "class:prompt",
                                f"{current_prefix}{current_separator}",
                            )
                        ]
                    ),
                    default=default_text,
                    validator=self.NonEmptyValidator(),
                    validate_while_typing=False,
                )
                # Hide cursor IMMEDIATELY after input is received, before any processing
                if hide_cursor:
                    self.hide_cursor()
                return result.strip()
            else:
                # For standard input, use our custom raw mode handling with prompt overrides
                result = await asyncio.get_event_loop().run_in_executor(
                    None, self._read_line_raw, prompt_prefix, prompt_separator
                )
                # Hide cursor is now handled directly in _read_line_raw
                # Check for special commands
                if result in ["edit", "retry", "exit"]:
                    return result
                # Handle empty input validation
                while not result.strip():
                    self.write_line()
                    result = await asyncio.get_event_loop().run_in_executor(
                        None, self._read_line_raw, prompt_prefix, prompt_separator
                    )
                    if result in ["edit", "retry", "exit"]:
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
        end_char = text[-1] if text.endswith(("?", "!")) else "."
        # Apply consistent styling to formatted prompts
        return f"{self._reset_style}{self._default_style}{self._prompt_prefix}{text.rstrip('?.!')}{end_char * 3}"

    def _prepare_display_update(self, content: str = None, prompt: str = None) -> str:
        """Prepare display update content without actually writing to terminal."""
        buffer = ""
        if content:
            # Apply reset before content to ensure consistent style
            buffer += self._reset_style + content
        if prompt:
            buffer += "\n"
        if prompt:
            # Prompt already includes reset styling from format_prompt
            buffer += prompt
        return buffer

    async def update_display(
        self, content: str = None, prompt: str = None, preserve_cursor: bool = False
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
        if (
            current_size.columns != self._last_size.columns
            or current_size.lines != self._last_size.lines
        ):
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
        return False  # Don't suppress exceptions
