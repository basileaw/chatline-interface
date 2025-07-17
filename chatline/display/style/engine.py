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
                        # Reset quote patterns on newlines to prevent runaway styling
                        reset_codes = self._reset_quote_patterns()
                        if reset_codes:
                            self.terminal.write(reset_codes)
                            styled_out += reset_codes
                        self._current_line_length = 0
                    else:
                        self._current_line_length += 1
                else:
                    self._word_buffer += char

            sys.stdout.flush()
            return chunk, styled_out

        finally:
            self.terminal.hide_cursor()

    def _is_apostrophe(self, text: str, pos: int) -> bool:
        """
        Check if a single quote at the given position is an apostrophe.
        
        An apostrophe is typically within a word (letters/digits on both sides)
        or at the end of a word for possessives/contractions.
        
        Args:
            text: The text string
            pos: Position of the single quote character
            
        Returns:
            True if the single quote is likely an apostrophe, False if it's a quote
        """
        if pos < 0 or pos >= len(text) or text[pos] != "'":
            return False
            
        # Check if preceded by a word character
        has_word_before = pos > 0 and (text[pos - 1].isalnum())
        
        # Check if followed by a word character
        has_word_after = pos < len(text) - 1 and (text[pos + 1].isalnum())
        
        # An apostrophe is:
        # 1. Between two word characters (e.g., "don't", "they're")
        # 2. At the end of a word preceded by a letter (e.g., "dogs'", "James'")
        if has_word_before and has_word_after:
            return True
        
        # Possessive apostrophe: preceded by letter, followed by 's', whitespace, or end of text
        if has_word_before:
            if pos == len(text) - 1:  # End of text (e.g., "dogs'")
                return True
            elif pos < len(text) - 1:
                next_char = text[pos + 1]
                if next_char == 's' or next_char.isspace():  # "James's" or "dogs' toys"
                    return True
                
        return False

    def _is_apostrophe_in_nested_quote(self, text: str, pos: int) -> bool:
        """
        Check if a single quote is an apostrophe when we're inside a nested quote.
        
        This is more restrictive than the general apostrophe detection because
        when inside a nested quote, single quotes are more likely to be closing
        quotes than possessive apostrophes.
        
        Args:
            text: The text string
            pos: Position of the single quote character
            
        Returns:
            True if the single quote is definitely an apostrophe (like in contractions)
        """
        if pos < 0 or pos >= len(text) or text[pos] != "'":
            return False
            
        # Check if preceded by a word character
        has_word_before = pos > 0 and (text[pos - 1].isalnum())
        
        # Check if followed by a word character
        has_word_after = pos < len(text) - 1 and (text[pos + 1].isalnum())
        
        # When inside nested quotes, only treat as apostrophe if it's clearly a contraction
        # (between two word characters) or followed by 's' in possessive
        if has_word_before and has_word_after:
            return True  # Contractions like "don't", "they're"
        
        # Be more restrictive about possessive apostrophes inside nested quotes
        if has_word_before and pos < len(text) - 1:
            next_char = text[pos + 1]
            if next_char == 's':  # Only "James's" style possessives
                return True
        
        # Don't treat quotes followed by spaces as apostrophes when inside nested quotes
        # These are more likely to be closing quotes
        return False

    def _reset_quote_patterns(self) -> str:
        """
        Reset quote-related patterns from active patterns stack.
        
        Returns ANSI codes to properly reset styles when quote patterns are removed.
        This is used as a safety valve to prevent runaway quote styling across line breaks.
        """
        if not self._active_patterns:
            return ""
            
        quote_patterns = ["quotes", "nested_quotes"]
        patterns_to_remove = []
        reset_codes = []
        
        # Find quote patterns in the active stack (from top to bottom)
        for i in range(len(self._active_patterns) - 1, -1, -1):
            pattern_name = self._active_patterns[i]
            if pattern_name in quote_patterns:
                patterns_to_remove.append(i)
                
        # Remove quote patterns and collect reset codes
        for index in patterns_to_remove:
            pattern_name = self._active_patterns[index]
            pattern = self.definitions.get_pattern(pattern_name)
            
            if pattern:
                # Emit OFF codes for removed styles
                if pattern.style:
                    for style_name in pattern.style:
                        reset_codes.append(self.definitions.get_format(f"{style_name}_OFF"))
                
                # Reset color if pattern had one
                if pattern.color:
                    reset_codes.append(self.definitions.get_format("COLOR_RESET"))
            
            # Remove from active patterns
            self._active_patterns.pop(index)
        
        # Rebuild current style state for remaining patterns
        if reset_codes:
            reset_codes.append(self._get_current_style())
            
        return "".join(reset_codes)

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

            # Check for multi-character delimiters first (longest to shortest)
            found_match = False
            max_delimiter_length = self.definitions.get_max_delimiter_length()

            # Try delimiters from longest to shortest (greedy matching)
            for delimiter_length in range(max_delimiter_length, 1, -1):
                if i + delimiter_length - 1 >= len(text):
                    continue  # Not enough characters left
                
                delimiter = text[i : i + delimiter_length]
                pattern_roles = self.definitions.get_pattern_by_delimiter(delimiter, self._active_patterns)

                # Check for active pattern end with multi-char delimiter
                if self._active_patterns:
                    active_pattern = self.definitions.get_pattern(
                        self._active_patterns[-1]
                    )
                    if active_pattern and delimiter in active_pattern.get_end_chars():
                        # End pattern if delimiter matches
                        if not active_pattern.remove_delimiters:
                            out.append(self._get_current_style() + delimiter)

                        # Check what styles need to be turned off
                        pattern_to_remove = self.definitions.get_pattern(
                            self._active_patterns[-1]
                        )
                        styles_to_remove = (
                            set(pattern_to_remove.style)
                            if pattern_to_remove and pattern_to_remove.style
                            else set()
                        )
                        had_color = pattern_to_remove and pattern_to_remove.color

                        self._active_patterns.pop()

                        # Emit OFF codes for removed styles
                        for style_name in styles_to_remove:
                            out.append(self.definitions.get_format(f"{style_name}_OFF"))

                        # If pattern had color, explicitly reset color before rebuilding style
                        if had_color:
                            out.append(self.definitions.get_format("COLOR_RESET"))

                        # Now apply current style state
                        out.append(self._get_current_style())
                        i += delimiter_length  # Skip all characters in delimiter
                        found_match = True
                        break  # Exit delimiter length loop

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
                        out.append(delimiter)
                    i += delimiter_length  # Skip all characters in delimiter
                    found_match = True
                    break  # Exit delimiter length loop
            
            # If we found a match, continue to next character
            if found_match:
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
                        # Don't end nested_quotes pattern for apostrophes
                        if char == "'" and active_pattern.name == "nested_quotes" and self._is_apostrophe_in_nested_quote(text, i):
                            # This is an apostrophe, not a closing quote - treat as regular char
                            out.append(char)
                            i += 1
                            found_match = True
                            continue
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
                        had_color = pattern_to_remove and pattern_to_remove.color

                        self._active_patterns.pop()

                        # Emit OFF codes for removed styles
                        for style_name in styles_to_remove:
                            out.append(self.definitions.get_format(f"{style_name}_OFF"))

                        # If pattern had color, explicitly reset color before rebuilding style
                        if had_color:
                            out.append(self.definitions.get_format("COLOR_RESET"))

                        # Now apply current style state
                        out.append(self._get_current_style())
                        i += 1  # Move to next character
                        found_match = True
                        continue

                # Check if char is a start delimiter for a new pattern
                pattern_roles = self.definitions.get_pattern_by_delimiter(char, self._active_patterns)
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

                # Check for single quotes that are apostrophes
                if char == "'":
                    # Don't style apostrophes in contractions
                    if self._is_apostrophe(text, i):
                        # This is an apostrophe, not a quote - treat as regular char
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
