# display/style/engine.py

import re
import sys
import asyncio
from io import StringIO
from rich.style import Style
from rich.console import Console
from typing import Dict, List, Optional, Tuple, Union, Set
from .definitions import StyleDefinitions, Pattern


class StyleEngine:
    """Engine for processing and applying text styles."""

    def __init__(self, terminal, definitions: StyleDefinitions, strategies):
        """Initialize engine with terminal, definitions, and strategies."""
        self.terminal = terminal
        self.definitions = definitions
        self.strategies = strategies

        # Init styling state
        self._base_color = self.definitions.get_format("RESET")
        self._active_patterns = []
        self._word_buffer = ""
        self._buffer_lock = asyncio.Lock()
        self._current_line_length = 0

        # Setup Rich console
        self._setup_rich_console()

    def _setup_rich_console(self) -> None:
        """Setup Rich console and styles."""
        self._rich_console = Console(
            force_terminal=True,
            color_system="truecolor",
            file=StringIO(),
            highlight=False,
        )
        self.rich_style = {
            name: Style(color=cfg["rich"])
            for name, cfg in self.definitions.colors.items()
        }

    def get_visible_length(self, text: str) -> int:
        """Return visible text length (ignores ANSI codes and box chars)."""
        # More comprehensive ANSI regex that works better with XTerm.js
        text = re.sub(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])", "", text)

        # Remove box drawing chars
        for c in self.definitions.box_chars:
            text = text.replace(c, "")

        # Calculate length accounting for multibyte Unicode characters
        # This ensures accurate length calculation for Unicode punctuation
        return len(text)

    def get_format(self, name: str) -> str:
        """Return format code for name."""
        return self.definitions.get_format(name)

    def get_base_color(self, color_name: str = "GREEN") -> str:
        """Return ANSI code for the given color (default 'GREEN')."""
        return self.definitions.get_color(color_name).get("ansi", "")

    def get_color(self, name: str) -> str:
        """Return ANSI code for color name."""
        return self.definitions.get_color(name).get("ansi", "")

    def get_rich_style(self, name: str) -> Style:
        """Return Rich style for name."""
        return self.rich_style.get(name, Style())

    def set_base_color(self, color: Optional[str] = None) -> None:
        """Set base text color."""
        self._base_color = (
            self.get_color(color) if color else self.definitions.get_format("RESET")
        )

    async def write_styled(self, chunk: str) -> Tuple[str, str]:
        """Process and write text chunk with styles; return (raw_text, styled_text)."""
        if not chunk:
            return "", ""

        async with self._buffer_lock:
            return self._process_and_write(chunk)

    def _process_and_write(self, chunk: str) -> Tuple[str, str]:
        """Process chunk: apply styles, wrap lines, and write output."""
        if not chunk:
            return "", ""

        self.terminal.hide_cursor()
        styled_out = ""

        try:
            if any(
                c in self.definitions.box_chars for c in chunk
            ):  # Handle box drawing chars separately
                self.terminal.write(chunk)
                return chunk, chunk

            for char in chunk:
                if char.isspace():
                    if self._word_buffer:  # Flush word buffer if exists
                        word_length = self.get_visible_length(self._word_buffer)
                        if (
                            self._current_line_length + word_length
                            >= self.terminal.width
                        ):  # Wrap line if needed
                            self.terminal.write("\n")
                            styled_out += "\n"
                            self._current_line_length = 0
                        styled_word = self._style_chunk(
                            self._word_buffer
                        )  # Style and write word
                        self.terminal.write(styled_word)
                        styled_out += styled_word
                        self._current_line_length += word_length
                        self._word_buffer = ""
                    self.terminal.write(char)  # Write space or newline
                    styled_out += char
                    if char == "\n":
                        self._current_line_length = 0
                    else:
                        self._current_line_length += 1
                else:
                    self._word_buffer += char

            sys.stdout.flush()
            return chunk, styled_out

        finally:
            self.terminal.hide_cursor()

    def _style_chunk(self, text: str) -> str:
        """Return text with applied active styles and handled delimiters."""
        if not text or any(c in self.definitions.box_chars for c in text):
            return text

        out = []

        if not self._active_patterns:  # Reset styles if no active patterns
            out.append(
                f"{self.definitions.get_format('ITALIC_OFF')}"
                f"{self.definitions.get_format('BOLD_OFF')}"
                f"{self._base_color}"
            )

        i = 0
        while i < len(text):
            # Apply style at word start
            if i == 0 or text[i - 1].isspace():
                out.append(self._get_current_style())

            char = text[i]

            # Skip styling for measurement patterns (e.g., 5'10", 6'2")
            if i > 0 and char == '"' and i < len(text) - 1:
                # Check if this looks like a measurement: digit followed by quote
                if text[i - 1] == "'" and i > 1 and text[i - 2].isdigit():
                    # This looks like an inch mark in a measurement like 6'5"
                    out.append(char)
                    i += 1
                    continue

            # Check for multi-character delimiters first
            found_match = False

            # Check if this could be the start of a multi-char delimiter
            if i + 1 < len(text):
                # Try two-character sequences (like ** or __)
                two_chars = text[i : i + 2]
                pattern_roles = self.definitions.get_pattern_by_delimiter(two_chars)

                # Check for active pattern end with multi-char delimiter
                if self._active_patterns:
                    active_pattern = self.definitions.get_pattern(
                        self._active_patterns[-1]
                    )
                    if active_pattern and two_chars in active_pattern.get_end_chars():
                        # End pattern if delimiter matches
                        if not active_pattern.remove_delimiters:
                            out.append(self._get_current_style() + two_chars)

                        # Check what styles need to be turned off
                        pattern_to_remove = self.definitions.get_pattern(
                            self._active_patterns[-1]
                        )
                        styles_to_remove = (
                            set(pattern_to_remove.style)
                            if pattern_to_remove and pattern_to_remove.style
                            else set()
                        )

                        self._active_patterns.pop()

                        # Emit OFF codes for removed styles
                        for style_name in styles_to_remove:
                            out.append(self.definitions.get_format(f"{style_name}_OFF"))

                        # Now apply current style state
                        out.append(self._get_current_style())
                        i += 2  # Skip both characters
                        found_match = True
                        continue

                # Check for new pattern start with multi-char delimiter
                start_pattern = None
                for pattern, is_start in pattern_roles:
                    if is_start:
                        start_pattern = pattern
                        break

                if start_pattern:
                    # Start new pattern with multi-char delimiter
                    self._active_patterns.append(start_pattern.name)
                    out.append(self._get_current_style())
                    if not start_pattern.remove_delimiters:
                        out.append(two_chars)
                    i += 2  # Skip both characters
                    found_match = True
                    continue

            # If no multi-char match was found, check for single-char delimiters
            if not found_match:
                # Skip styling for specific contexts of punctuation marks

                # Check if current char is an end delimiter for active pattern
                if self._active_patterns:
                    active_pattern = self.definitions.get_pattern(
                        self._active_patterns[-1]
                    )
                    if active_pattern and char in active_pattern.get_end_chars():
                        # End pattern if delimiter matches
                        if not active_pattern.remove_delimiters:
                            out.append(self._get_current_style() + char)

                        # Check what styles need to be turned off
                        pattern_to_remove = self.definitions.get_pattern(
                            self._active_patterns[-1]
                        )
                        styles_to_remove = (
                            set(pattern_to_remove.style)
                            if pattern_to_remove and pattern_to_remove.style
                            else set()
                        )

                        self._active_patterns.pop()

                        # Emit OFF codes for removed styles
                        for style_name in styles_to_remove:
                            out.append(self.definitions.get_format(f"{style_name}_OFF"))

                        # Now apply current style state
                        out.append(self._get_current_style())
                        i += 1  # Move to next character
                        found_match = True
                        continue

                # Check if char is a start delimiter for a new pattern
                pattern_roles = self.definitions.get_pattern_by_delimiter(char)
                start_pattern = None

                # Check for quote marks in contexts where they shouldn't be styled
                if char == '"' or char == "\u201c" or char == "\u201d":
                    # Don't style quotes that appear after numbers or in other non-dialogue contexts
                    if i > 0 and (text[i - 1].isdigit() or text[i - 1] == "'"):
                        # This is likely a measurement or similar - treat as regular char
                        out.append(char)
                        i += 1
                        found_match = True
                        continue

                # Normal pattern detection
                for pattern, is_start in pattern_roles:
                    if is_start:
                        start_pattern = pattern
                        break

                if start_pattern:
                    # Start new pattern with single-char delimiter
                    self._active_patterns.append(start_pattern.name)
                    out.append(self._get_current_style())
                    if not start_pattern.remove_delimiters:
                        out.append(char)
                    i += 1  # Move to next character
                    found_match = True
                    continue

            # If we get here, it's a regular character
            if not found_match:
                out.append(char)
                i += 1

        return "".join(out)

    def _get_current_style(self) -> str:
        """Return combined ANSI style string for active patterns."""
        style = [self._base_color]
        for name in self._active_patterns:
            pattern = self.definitions.get_pattern(name)
            if pattern and pattern.color:
                style[0] = self.definitions.get_color(pattern.color)["ansi"]
            if pattern and pattern.style:
                style.extend(
                    self.definitions.get_format(f"{s}_ON") for s in pattern.style
                )
        return "".join(style)

    async def flush_styled(self) -> Tuple[str, str]:
        """Flush remaining text, reset state, and return (raw_text, styled_text)."""
        styled_out = ""
        try:
            if self._word_buffer:  # Flush remaining word buffer
                word_length = self.get_visible_length(self._word_buffer)
                if self._current_line_length + word_length >= self.terminal.width:
                    self.terminal.write("\n")
                    styled_out += "\n"
                    self._current_line_length = 0
                styled_word = self._style_chunk(self._word_buffer)
                self.terminal.write(styled_word)
                styled_out += styled_word
                self._word_buffer = ""
            if not styled_out.endswith("\n"):  # Ensure ending newline
                self.terminal.write("\n")
                styled_out += "\n"
            self.terminal.write(self.definitions.get_format("RESET"))  # Reset styles
            sys.stdout.flush()
            self._reset_output_state()
            return "", styled_out
        finally:
            self.terminal.hide_cursor()

    def _reset_output_state(self) -> None:
        """Reset internal styling state."""
        self._active_patterns.clear()
        self._word_buffer = ""
        self._current_line_length = 0

    def append_single_blank_line(self, text: str) -> str:
        """Ensure text ends with one blank line."""
        return text.rstrip("\n") + "\n\n" if text.strip() else text

    def set_output_color(self, color: Optional[str] = None) -> None:
        """Alias for set_base_color; set output text color."""
        self.set_base_color(color)

    def set_base_color(self, color: Optional[str] = None) -> None:
        """Set base text color."""
        self._base_color = (
            self.get_color(color) if color else self.definitions.get_format("RESET")
        )
