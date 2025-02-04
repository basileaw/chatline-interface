# styles.py

import re, sys, asyncio
from dataclasses import dataclass
from rich.style import Style
from rich.console import Console
from rich.panel import Panel
from rich.align import Align
from io import StringIO

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
    'BLUE':  {'ansi': '\033[38;5;75m', 'rich': 'blue1'},
    'GRAY':  {'ansi': '\033[38;5;245m','rich': 'gray50'},
    'YELLOW': {'ansi': '\033[38;5;227m','rich': 'yellow1'},
    'WHITE': {'ansi': '\033[38;5;255m','rich': 'white'}
}
BOX_CHARS = {'─','│','╭','╮','╯','╰'}

@dataclass
class Pattern:
    name: str
    start: str
    end: str
    color: str = None
    styles: list = None
    remove_delimiters: bool = False

class DisplayStrategy:
    def format(self, content): pass
    def get_visible_length(self, text): pass

class TextDisplayStrategy:
    def __init__(self, styles): 
        self.styles = styles
        
    def format(self, content): 
        return content.text + "\n"
        
    def get_visible_length(self, text): 
        return self.styles.get_visible_length(text)

class PanelDisplayStrategy:
    def __init__(self, styles):
        self.styles = styles
        self.console = Console(force_terminal=True, color_system="truecolor", record=True)
        
    def format(self, content):
        with self.console.capture() as c:
            self.console.print(
                Panel(
                    Align.center(content.text.rstrip()),  # Wrap content with Align.center()
                    title="Baze Inc.",
                    title_align="right",
                    border_style="dim yellow",
                    style=content.color or "on grey23",
                    padding=(1, 2),
                    expand=True
                )
            )
        return c.get()
        
    def get_visible_length(self, text):
        return self.styles.get_visible_length(text) + 4

class Styles:
    def __init__(self, terminal=None):
        self.terminal = terminal
        self._init_patterns()
        self._init_state()

    def _init_patterns(self):
        patterns = {
            'quotes':   {'start': '"', 'end': '"', 'color': 'PINK'},
            'brackets': {'start': '[', 'end': ']', 'color': 'GRAY','styles': ['ITALIC'], 'remove_delimiters': True},
            'emphasis': {'start': '_', 'end': '_', 'color': None, 'styles': ['ITALIC'], 'remove_delimiters': True},
            'strong':   {'start': '*', 'end': '*', 'color': None, 'styles': ['BOLD'],   'remove_delimiters': True}
        }
        patterns.update({k:{**v,'styles':[],'remove_delimiters':False} for k,v in list(patterns.items())[:1]})
        
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

    def _init_state(self):
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

    def create_display_strategy(self, strategy_type):
        strategies = {
            "text": TextDisplayStrategy(self),
            "panel": PanelDisplayStrategy(self)
        }
        if strategy_type not in strategies:
            raise ValueError(f"Unknown strategy type: {strategy_type}")
        return strategies[strategy_type]

    def get_visible_length(self, text):
        text = ANSI_REGEX.sub('', text)
        for c in BOX_CHARS: text = text.replace(c, '')
        return len(text)

    def append_single_blank_line(self, text):
        return text.rstrip('\n') + "\n\n" if text.strip() else text

    def get_format(self, name): return FORMATS.get(name, '')
    def get_color(self, name): return COLORS.get(name, {}).get('ansi', '')
    def get_rich_style(self, name): return self.rich_styles.get(name, Style())
    def get_base_color(self, color_name='GREEN'): return COLORS.get(color_name, {}).get('ansi', '')
    def set_output_color(self, color=None): 
        self._base_color = self.get_color(color) if color else FORMATS['RESET']

    def get_style(self, active_patterns, base_color):
        style = [base_color]
        for name in active_patterns:
            pat = self.by_name[name]
            if pat.color: style[0] = COLORS[pat.color]['ansi']
            style.extend(FORMATS[f'{s}_ON'] for s in (pat.styles or []))
        return ''.join(style)

    def split_into_styled_words(self, text):
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

    def format_styled_lines(self, lines, base_color):
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
            if formatted: res.append(formatted)
            
        extra = self.get_format('RESET') + base_color
        return "\n".join(res) + (extra if curr_style != extra else "")

    def _style_chunk(self, text):
        if not text or any(c in BOX_CHARS for c in text): return text

        out = []
        if not self._active_patterns:
            out.append(f"{FORMATS['ITALIC_OFF']}{FORMATS['BOLD_OFF']}{self._base_color}")

        for i, char in enumerate(text):
            if i == 0 or text[i-1].isspace():
                out.append(self.get_style(self._active_patterns, self._base_color))

            if (self._active_patterns and char in self.end_map and 
                    char == self.by_name[self._active_patterns[-1]].end):
                pat = self.by_name[self._active_patterns[-1]]
                if not pat.remove_delimiters:
                    out.append(self.get_style(self._active_patterns, self._base_color) + char)
                self._active_patterns.pop()
                out.append(self.get_style(self._active_patterns, self._base_color))
                continue

            if char in self.start_map:
                new_pat = self.start_map[char]
                self._active_patterns.append(new_pat.name)
                out.append(self.get_style(self._active_patterns, self._base_color))
                if not new_pat.remove_delimiters:
                    out.append(char)
                continue

            out.append(char)

        return ''.join(out)

    async def write_styled(self, chunk):
        if not chunk: return "", ""
        async with self._buffer_lock:
            return self._process_and_write(chunk)

    def _process_and_write(self, chunk):
        if not chunk: return "", ""
        if self.terminal: self.terminal._hide_cursor()

        styled_out = ""
        try:
            if any(c in BOX_CHARS for c in chunk):
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
            if self.terminal: self.terminal._hide_cursor()

    async def flush_styled(self):
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
            if self.terminal: self.terminal._hide_cursor()

    def _reset_output_state(self):
        self._active_patterns.clear()
        self._word_buffer = ""
        self._current_line_length = 0
