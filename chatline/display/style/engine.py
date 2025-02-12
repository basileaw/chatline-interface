# display/style/engine.py

import re
import sys
import asyncio
from io import StringIO
from rich.style import Style
from rich.console import Console
from typing import Dict, List, Optional, Tuple, Union
from .definitions import StyleDefinitions

class StyleEngine:
    """Engine for processing and applying text styles."""
    def __init__(self, terminal, definitions: StyleDefinitions, strategies):
        """Initialize engine with terminal, definitions, and strategies."""
        self.terminal = terminal
        self.definitions = definitions
        self.strategies = strategies

        # Init styling state
        self._base_color = self.definitions.get_format('RESET')
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
            highlight=False
        )
        self.rich_style = {
            name: Style(color=cfg['rich'])
            for name, cfg in self.definitions.colors.items()
        }

    def get_visible_length(self, text: str) -> int:
        """Return visible text length (ignores ANSI codes and box chars)."""
        text = re.sub(r'\x1B\[[0-?]*[ -/]*[@-~]', '', text)  # Remove ANSI sequences
        for c in self.definitions.box_chars:  # Remove box drawing chars
            text = text.replace(c, '')
        return len(text)

    def get_format(self, name: str) -> str:
        """Return format code for name."""
        return self.definitions.get_format(name)

    def get_base_color(self, color_name: str = 'GREEN') -> str:
        """Return ANSI code for the given color (default 'GREEN')."""
        return self.definitions.get_color(color_name).get('ansi', '')

    def get_color(self, name: str) -> str:
        """Return ANSI code for color name."""
        return self.definitions.get_color(name).get('ansi', '')

    def get_rich_style(self, name: str) -> Style:
        """Return Rich style for name."""
        return self.rich_style.get(name, Style())

    def set_base_color(self, color: Optional[str] = None) -> None:
        """Set base text color."""
        self._base_color = (self.get_color(color) if color
                            else self.definitions.get_format('RESET'))

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
            if any(c in self.definitions.box_chars for c in chunk):  # Handle box drawing chars separately
                self.terminal.write(chunk)
                return chunk, chunk

            for char in chunk:
                if char.isspace():
                    if self._word_buffer:  # Flush word buffer if exists
                        word_length = self.get_visible_length(self._word_buffer)
                        if self._current_line_length + word_length >= self.terminal.width:  # Wrap line if needed
                            self.terminal.write('\n')
                            styled_out += '\n'
                            self._current_line_length = 0
                        styled_word = self._style_chunk(self._word_buffer)  # Style and write word
                        self.terminal.write(styled_word)
                        styled_out += styled_word
                        self._current_line_length += word_length
                        self._word_buffer = ""
                    self.terminal.write(char)  # Write space or newline
                    styled_out += char
                    if char == '\n':
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
            out.append(f"{self.definitions.get_format('ITALIC_OFF')}"
                       f"{self.definitions.get_format('BOLD_OFF')}"
                       f"{self._base_color}")

        for i, char in enumerate(text):
            if i == 0 or text[i - 1].isspace():  # Apply style at word start
                out.append(self._get_current_style())

            active_pattern = (self.definitions.get_pattern(self._active_patterns[-1])
                              if self._active_patterns else None)
            if active_pattern and char == active_pattern.end:  # End pattern if delimiter matches
                if not active_pattern.remove_delimiters:
                    out.append(self._get_current_style() + char)
                self._active_patterns.pop()
                out.append(self._get_current_style())
                continue

            new_pattern = next((p for p in self.definitions.patterns.values()
                                if p.start == char), None)
            if new_pattern:  # Start new pattern if applicable
                self._active_patterns.append(new_pattern.name)
                out.append(self._get_current_style())
                if not new_pattern.remove_delimiters:
                    out.append(char)
                continue

            out.append(char)

        return ''.join(out)

    def _get_current_style(self) -> str:
        """Return combined ANSI style string for active patterns."""
        style = [self._base_color]
        for name in self._active_patterns:
            pattern = self.definitions.get_pattern(name)
            if pattern and pattern.color:
                style[0] = self.definitions.get_color(pattern.color)['ansi']
            if pattern and pattern.style:
                style.extend(self.definitions.get_format(f'{s}_ON') for s in pattern.style)
        return ''.join(style)

    async def flush_styled(self) -> Tuple[str, str]:
        """Flush remaining text, reset state, and return (raw_text, styled_text)."""
        styled_out = ""
        try:
            if self._word_buffer:  # Flush remaining word buffer
                word_length = self.get_visible_length(self._word_buffer)
                if self._current_line_length + word_length >= self.terminal.width:
                    self.terminal.write('\n')
                    styled_out += '\n'
                    self._current_line_length = 0
                styled_word = self._style_chunk(self._word_buffer)
                self.terminal.write(styled_word)
                styled_out += styled_word
                self._word_buffer = ""
            if not styled_out.endswith('\n'):  # Ensure ending newline
                self.terminal.write("\n")
                styled_out += "\n"
            self.terminal.write(self.definitions.get_format('RESET'))  # Reset styles
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
        return text.rstrip('\n') + "\n\n" if text.strip() else text

    def set_output_color(self, color: Optional[str] = None) -> None:
        """Alias for set_base_color; set output text color."""
        self.set_base_color(color)

    def set_base_color(self, color: Optional[str] = None) -> None:
        """Set base text color."""
        self._base_color = (self.get_color(color) if color
                            else self.definitions.get_format('RESET'))
