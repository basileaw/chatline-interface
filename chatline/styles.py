# styles.py

import re
import sys
import asyncio
from typing import List, Optional, Dict, Tuple, Protocol, TYPE_CHECKING
from dataclasses import dataclass
from rich.style import Style
from rich.console import Console
from rich.panel import Panel
from io import StringIO

if TYPE_CHECKING:
    from .conversation import PrefaceContent

# Constants for styling and formatting
ANSI_REGEX = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
FMT = lambda x: f'\033[{x}m'
FORMATS = {
    'RESET': FMT('0'),
    'ITALIC_ON': FMT('3'),
    'ITALIC_OFF': FMT('23'),
    'BOLD_ON': FMT('1'),
    'BOLD_OFF': FMT('22')
}
COLORS = {
    'GREEN': {'ansi': '\033[38;5;47m', 'rich': 'green3'},
    'PINK':  {'ansi': '\033[38;5;212m','rich': 'pink1'},
    'BLUE':  {'ansi': '\033[38;5;75m', 'rich': 'blue1'}
}
SPECIAL_CHARS = ['─','│','╭','╮','╯','╰']
BOX_CHARS = set(SPECIAL_CHARS)

@dataclass
class Pattern:
    name: str
    start: str
    end: str
    color: Optional[str]
    styles: List[str] = None
    remove_delimiters: bool = False

class DisplayStrategy(Protocol):
    def format(self, content: 'PrefaceContent') -> str: ...
    def get_visible_length(self, text: str) -> int: ...

class TextDisplayStrategy:
    def __init__(self, styles): 
        self.styles = styles
        
    def format(self, content: 'PrefaceContent') -> str: 
        return content.text + "\n"
        
    def get_visible_length(self, text: str) -> int: 
        return self.styles.get_visible_length(text)

class PanelDisplayStrategy:
    def __init__(self, styles):
        self.styles = styles
        self.console = Console(force_terminal=True, color_system="truecolor", record=True)
        
    def format(self, content: 'PrefaceContent') -> str:
        with self.console.capture() as c:
            self.console.print(Panel(content.text.rstrip(), style=content.color or ""))
        return c.get()
        
    def get_visible_length(self, text: str) -> int:
        return self.styles.get_visible_length(text) + 4

class Styles:
    def __init__(self, terminal=None):
        self.terminal = terminal
        self._init_patterns()
        self._init_state()

    def _init_patterns(self) -> None:
        """Initialize style patterns and mappings."""
        patterns = {
            'quotes':   {'start': '"', 'end': '"', 'color': 'PINK'},
            'brackets': {'start': '[', 'end': ']', 'color': 'BLUE'},
            'emphasis': {'start': '_', 'end': '_', 'color': None, 'styles': ['ITALIC'], 'remove_delimiters': True},
            'strong':   {'start': '*', 'end': '*', 'color': None, 'styles': ['BOLD'],   'remove_delimiters': True}
        }
        # Add non-removing patterns
        patterns.update({
            k:{**v,'styles':[],'remove_delimiters':False}
            for k,v in list(patterns.items())[:2]
        })
        
        self.by_name = {}
        self.start_map = {}
        self.end_map = {}
        used = set()
        
        for name, cfg in patterns.items():
            pat = Pattern(name=name, **cfg)
            if pat.start in used or pat.end in used:
                raise ValueError(f"Duplicate delimiter in '{pat.name}'")
            used.update([pat.start, pat.end])
            self.by_name[name] = self.start_map[pat.start] = self.end_map[pat.end] = pat
            
        self.rich_styles = {n:Style(color=c['rich']) for n,c in COLORS.items()}

    def _init_state(self) -> None:
        """Initialize output state."""
        self._base_color = FORMATS['RESET']
        self._active_patterns = []
        self._current_line_length = 0
        self._word_buffer = ""
        self._buffer_lock = asyncio.Lock()
        self._rich_console = Console(
            force_terminal=True,
            color_system="truecolor",
            file=StringIO(),
            highlight=False
        )

    def create_display_strategy(self, strategy_type: str) -> DisplayStrategy:
        strategies = {
            "text": TextDisplayStrategy(self),
            "panel": PanelDisplayStrategy(self)
        }
        if strategy_type not in strategies:
            raise ValueError(f"Unknown strategy type: {strategy_type}")
        return strategies[strategy_type]

    def get_visible_length(self, text: str) -> int:
        """Calculate visible length excluding ANSI and box chars."""
        text = ANSI_REGEX.sub('', text)
        for c in SPECIAL_CHARS:
            text = text.replace(c, '')
        return len(text)

    def has_box_chars(self, text: str) -> bool:
        """Check if text contains box-drawing characters."""
        return any(c in BOX_CHARS for c in text)

    def append_single_blank_line(self, text: str) -> str:
        """Append a single blank line to non-empty text."""
        if text.strip():
            return text.rstrip('\n') + "\n\n"
        return text

    def get_format(self, name: str) -> str:
        return FORMATS.get(name, '')

    def get_color(self, name: str) -> str:
        return COLORS.get(name, {}).get('ansi', '')

    def get_rich_style(self, name: str) -> Style:
        return self.rich_styles.get(name, Style())

    def get_base_color(self, color_name: str = 'GREEN') -> str:
        return COLORS.get(color_name, {}).get('ansi', '')

    def set_output_color(self, color: Optional[str] = None) -> None:
        self._base_color = self.get_color(color) if color else FORMATS['RESET']

    def split_into_styled_words(self, text: str) -> List[dict]:
        """Split text into styled words preserving formatting."""
        words = []
        curr = {'word':[],'styled':[],'patterns':[]}
        
        for i,char in enumerate(text):
            if char in self.start_map:
                pat = self.start_map[char]
                curr['patterns'].append(pat.name)
                if not pat.remove_delimiters:
                    curr['word'].append(char)
                    curr['styled'].append(char)
            elif curr['patterns'] and char in self.end_map:
                pat = self.by_name[curr['patterns'][-1]]
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
                    curr = {'word':[],'styled':[],'patterns':[]}
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

    def get_style(self, active_patterns: List[str], base_color: str) -> str:
        """Generate style string from patterns and base color."""
        style = [base_color]
        for name in active_patterns:
            pat = self.by_name[name]
            if pat.color:
                style[0] = COLORS[pat.color]['ansi']
            style.extend(FORMATS[f'{s}_ON'] for s in (pat.styles or []))
        return ''.join(style)

    def _style_chunk(self, text: str) -> str:
        """Apply styling to a chunk of text."""
        if not text or self.has_box_chars(text):
            return text

        out = []
        if not self._active_patterns:
            out.append(f"{FORMATS['ITALIC_OFF']}{FORMATS['BOLD_OFF']}{self._base_color}")

        for i, char in enumerate(text):
            # Reset style at word boundaries
            if i == 0 or text[i-1].isspace():
                out.append(self.get_style(self._active_patterns, self._base_color))

            # Handle pattern end
            if (self._active_patterns and char in self.end_map and 
                    char == self.by_name[self._active_patterns[-1]].end):
                pat = self.by_name[self._active_patterns[-1]]
                if not pat.remove_delimiters:
                    out.append(self.get_style(self._active_patterns, self._base_color) + char)
                self._active_patterns.pop()
                out.append(self.get_style(self._active_patterns, self._base_color))
                continue

            # Handle pattern start
            if char in self.start_map:
                new_pat = self.start_map[char]
                self._active_patterns.append(new_pat.name)
                out.append(self.get_style(self._active_patterns, self._base_color))
                if not new_pat.remove_delimiters:
                    out.append(char)
                continue

            out.append(char)

        return ''.join(out)

    def format_styled_lines(self, lines: List[List[dict]], base_color: str) -> str:
        """Format lines with proper styling."""
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

    async def write_styled(self, chunk: str) -> Tuple[str, str]:
        """Write styled text with buffering."""
        if not chunk:
            return "", ""

        async with self._buffer_lock:
            return self._process_and_write(chunk)

    def _process_and_write(self, chunk: str) -> Tuple[str, str]:
        """Process and write a chunk of text."""
        if not chunk:
            return "", ""

        if self.terminal:
            self.terminal._hide_cursor()

        styled_out = ""
        try:
            if self.has_box_chars(chunk):
                sys.stdout.write(chunk)
                styled_out = chunk
            else:
                for char in chunk:
                    if char.isspace():
                        if self._word_buffer:
                            styled_word = self._style_chunk(self._word_buffer)
                            sys.stdout.write(styled_word)
                            styled_out += styled_word
                            self._word_buffer = ""
                        sys.stdout.write(char)
                        styled_out += char
                        self._current_line_length = 0 if char == '\n' else self._current_line_length + 1
                    else:
                        self._word_buffer += char
            sys.stdout.flush()
            return chunk, styled_out
        finally:
            if self.terminal:
                self.terminal._hide_cursor()

    async def flush_styled(self) -> Tuple[str, str]:
        """Flush remaining styled content."""
        styled_out = ""
        try:
            if self._word_buffer:
                styled_word = self._style_chunk(self._word_buffer)
                sys.stdout.write(styled_word)
                styled_out += styled_word
                self._word_buffer = ""

            if self._current_line_length > 0:
                sys.stdout.write("\n")
                styled_out += "\n"

            sys.stdout.write(FORMATS['RESET'])
            sys.stdout.flush()
            self._reset_output_state()
            return "", styled_out
        finally:
            if self.terminal:
                self.terminal._hide_cursor()

    def _reset_output_state(self) -> None:
        """Reset all output state."""
        self._active_patterns.clear()
        self._word_buffer = ""
        self._current_line_length = 0