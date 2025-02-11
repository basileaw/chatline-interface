# style/application.py

import re
import sys
import asyncio
from io import StringIO
from rich.style import Style
from rich.console import Console
from typing import Dict, List, Optional, Tuple, Type, Protocol, Union

class DisplayStrategyProtocol(Protocol):
    """Protocol defining the interface for display strategies."""
    def format(self, content: Union[Dict, object]) -> str: ...
    def get_visible_length(self, text: str) -> int: ...

class StyleEngine:
    """
    Applies styles to text content, managing style definitions,
    display strategies, and terminal output.
    """
    def __init__(self, terminal, definitions, strategies: Dict[str, Type[DisplayStrategyProtocol]]):
        """Initialize with terminal and style definitions."""
        self.terminal = terminal
        self.definitions = definitions
        self.strategies = strategies
        
        # Initialize internal style state
        self._base_color = self.definitions.formats['RESET']
        self._active_patterns = []
        self._word_buffer = ""
        self._buffer_lock = asyncio.Lock()
        self._current_line_length = 0
        self.term_width = self.terminal.term_width if self.terminal else 80
        
        # Initialize Rich console
        self._rich_console = Console(
            force_terminal=True,
            color_system="truecolor",
            file=StringIO(),
            highlight=False
        )
        self.rich_styles = {
            name: Style(color=cfg['rich'])
            for name, cfg in self.definitions.colors.items()
        }

    def create_display_strategy(self, strategy_type: str) -> DisplayStrategyProtocol:
        """Return a display strategy instance."""
        if strategy_type not in self.strategies:
            raise ValueError(f"Unknown strategy type: {strategy_type}")
        return self.strategies[strategy_type](self)

    def get_visible_length(self, text: str) -> int:
        """Return visible length of text without ANSI codes or box chars."""
        text = re.sub(r'\x1B\[[0-?]*[ -/]*[@-~]', '', text)
        for c in self.definitions.box_chars:
            text = text.replace(c, '')
        return len(text)

    def append_single_blank_line(self, text: str) -> str:
        """Ensure text ends with one blank line."""
        return text.rstrip('\n') + "\n\n" if text.strip() else text

    def get_format(self, name: str) -> str:
        """Return format code by name."""
        return self.definitions.formats.get(name, '')

    def get_color(self, name: str) -> str:
        """Return ANSI color code by name."""
        return self.definitions.colors.get(name, {}).get('ansi', '')

    def get_rich_style(self, name: str) -> Style:
        """Return Rich style by name."""
        return self.rich_styles.get(name, Style())

    def get_base_color(self, color_name: str = 'GREEN') -> str:
        """Return base ANSI color code."""
        return self.definitions.colors.get(color_name, {}).get('ansi', '')

    def set_output_color(self, color: Optional[str] = None) -> None:
        """Set the base output color."""
        self._base_color = self.get_color(color) if color else self.definitions.formats['RESET']

    def get_style(self, active_patterns: List[str], base_color: str) -> str:
        """Return combined style string for active patterns."""
        style = [base_color]
        for name in active_patterns:
            pat = self.definitions.patterns[name]
            if pat.color:
                style[0] = self.definitions.colors[pat.color]['ansi']
            style.extend(self.definitions.formats[f'{s}_ON'] for s in (pat.styles or []))
        return ''.join(style)

    def split_into_styled_words(self, text: str) -> List[Dict]:
        """Split text into words with style info."""
        words = []
        curr = {'word': [], 'styled': [], 'patterns': []}
        for char in text:
            if char in {p.start for p in self.definitions.patterns.values()}:
                pat = next(p for p in self.definitions.patterns.values() if p.start == char)
                curr['patterns'].append(pat.name)
                if not pat.remove_delimiters:
                    curr['word'].append(char)
                    curr['styled'].append(char)
            elif curr['patterns'] and char in {p.end for p in self.definitions.patterns.values()}:
                pat = self.definitions.patterns[curr['patterns'][-1]]
                if char == pat.end:
                    if not pat.remove_delimiters:
                        curr['word'].append(char)
                        curr['styled'].append(char)
                    curr['patterns'].pop()
            elif char.isspace():
                if curr['word']:
                    words.append({
                        'raw_text': ''.join(curr['word']),
                        'styled_text': ''.join(curr['styled']),
                        'active_patterns': curr['patterns'].copy()
                    })
                    curr = {'word': [], 'styled': [], 'patterns': []}
            else:
                curr['word'].append(char)
                curr['styled'].append(char)
        if curr['word']:
            words.append({
                'raw_text': ''.join(curr['word']),
                'styled_text': ''.join(curr['styled']),
                'active_patterns': curr['patterns'].copy()
            })
        return words

    def format_styled_lines(self, lines: List[Dict], base_color: str) -> str:
        """Format lines of styled words."""
        res = []
        curr_style = self.get_format('RESET') + base_color
        for line in lines:
            c = [curr_style]
            for word in line:
                s = self.get_style(word['active_patterns'], base_color)
                if s != curr_style:
                    c.append(s)
                    curr_style = s
                c.append(word['styled_text'] + " ")
            formatted = "".join(c).rstrip()
            if formatted:
                res.append(formatted)
        extra = self.get_format('RESET') + base_color
        return "\n".join(res) + (extra if curr_style != extra else "")

    def _style_chunk(self, text: str) -> str:
        """Apply styling to a text chunk."""
        if not text or any(c in self.definitions.box_chars for c in text):
            return text

        out = []
        if not self._active_patterns:
            out.append(f"{self.definitions.formats['ITALIC_OFF']}"
                       f"{self.definitions.formats['BOLD_OFF']}"
                       f"{self._base_color}")

        for i, char in enumerate(text):
            if i == 0 or text[i - 1].isspace():
                out.append(self.get_style(self._active_patterns, self._base_color))
            if (self._active_patterns and 
                char in {p.end for p in self.definitions.patterns.values()} and
                char == self.definitions.patterns[self._active_patterns[-1]].end):
                pat = self.definitions.patterns[self._active_patterns[-1]]
                if not pat.remove_delimiters:
                    out.append(self.get_style(self._active_patterns, self._base_color) + char)
                self._active_patterns.pop()
                out.append(self.get_style(self._active_patterns, self._base_color))
                continue
            if char in {p.start for p in self.definitions.patterns.values()}:
                new_pat = next(p for p in self.definitions.patterns.values() if p.start == char)
                self._active_patterns.append(new_pat.name)
                out.append(self.get_style(self._active_patterns, self._base_color))
                if not new_pat.remove_delimiters:
                    out.append(char)
                continue
            out.append(char)
        return ''.join(out)

    async def write_styled(self, chunk: str) -> Tuple[str, str]:
        """Write styled text and return (raw, styled) output."""
        if not chunk:
            return "", ""
        async with self._buffer_lock:
            return self._process_and_write(chunk)

    def _process_and_write(self, chunk: str) -> Tuple[str, str]:
        """Process and write text with styling."""
        if not chunk:
            return "", ""
        if self.terminal:
            self.terminal.hide_cursor()
        styled_out = ""
        try:
            if any(c in self.definitions.box_chars for c in chunk):
                sys.stdout.write(chunk)
                styled_out = chunk
            else:
                for char in chunk:
                    if char.isspace():
                        if self._word_buffer:
                            word_length = self.get_visible_length(self._word_buffer)
                            if self._current_line_length + word_length >= self.term_width:
                                sys.stdout.write('\n')
                                styled_out += '\n'
                                self._current_line_length = 0
                            styled_word = self._style_chunk(self._word_buffer)
                            sys.stdout.write(styled_word)
                            styled_out += styled_word
                            self._current_line_length += word_length
                            self._word_buffer = ""
                        sys.stdout.write(char)
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
            if self.terminal:
                self.terminal.hide_cursor()

    async def flush_styled(self) -> Tuple[str, str]:
        """Flush any remaining styled text."""
        styled_out = ""
        try:
            if self._word_buffer:
                word_length = self.get_visible_length(self._word_buffer)
                if self._current_line_length + word_length >= self.term_width:
                    sys.stdout.write('\n')
                    styled_out += '\n'
                    self._current_line_length = 0
                styled_word = self._style_chunk(self._word_buffer)
                sys.stdout.write(styled_word)
                styled_out += styled_word
                self._word_buffer = ""
            if not styled_out.endswith('\n'):
                sys.stdout.write("\n")
                styled_out += "\n"
            sys.stdout.write(self.definitions.formats['RESET'])
            sys.stdout.flush()
            self._reset_output_state()
            return "", styled_out
        finally:
            if self.terminal:
                self.terminal.hide_cursor()

    def _reset_output_state(self) -> None:
        """Reset internal output state."""
        self._active_patterns.clear()
        self._word_buffer = ""
        self._current_line_length = 0