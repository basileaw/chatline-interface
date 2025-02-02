# styles.py

import re
import sys
import asyncio
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass
from rich.style import Style
from rich.console import Console
from rich.panel import Panel
from io import StringIO

# Original Styles-related constants
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
STYLE_PATTERNS = {
    'quotes':   {'start': '"', 'end': '"', 'color': 'PINK'},
    'brackets': {'start': '[', 'end': ']', 'color': 'BLUE'},
    'emphasis': {'start': '_', 'end': '_', 'color': None, 'styles': ['ITALIC'], 'remove_delimiters': True},
    'strong':   {'start': '*', 'end': '*', 'color': None, 'styles': ['BOLD'],   'remove_delimiters': True}
}
STYLE_PATTERNS.update({
    k:{**v,'styles':[],'remove_delimiters':False}
    for k,v in list(STYLE_PATTERNS.items())[:2]
})

@dataclass
class Pattern:
    name: str
    start: str
    end: str
    color: Optional[str]
    styles: List[str] = None
    remove_delimiters: bool = False

class Styles:
    # [Original Styles class implementation remains exactly the same]
    def __init__(self):
        self.by_name,self.start_map,self.end_map={}, {}, {}
        used=set()
        for name,cfg in STYLE_PATTERNS.items():
            pat=Pattern(name=name,**cfg)
            if pat.start in used or pat.end in used:
                raise ValueError(f"Duplicate delimiter in '{pat.name}'")
            used.update([pat.start, pat.end])
            self.by_name[name]=self.start_map[pat.start]=self.end_map[pat.end]=pat
        self.rich_styles={n:Style(color=c['rich']) for n,c in COLORS.items()}

    def get_format(self, name:str) -> str: return FORMATS.get(name,'')
    def get_color(self, name:str) -> str: return COLORS.get(name,{}).get('ansi','')
    def get_rich_style(self, name:str) -> Style: return self.rich_styles.get(name,Style())
    def get_base_color(self, color_name:str='GREEN')->str: return COLORS.get(color_name,{}).get('ansi','')

    def get_visible_length(self, text:str) -> int:
        text=ANSI_REGEX.sub('', text)
        for c in ['─','│','╭','╮','╯','╰']: text=text.replace(c,'')
        return len(text)

    def get_style(self, active_patterns:List[str], base_color:str)->str:
        style=[base_color]
        for n in active_patterns:
            pat=self.by_name[n]
            if pat.color: style[0]=COLORS[pat.color]['ansi']
            style.extend(FORMATS[f'{s}_ON'] for s in (pat.styles or []))
        return ''.join(style)

    def split_text(self, text:str, width:Optional[int]=None)->List[str]:
        if width is None: width=80
        has_borders='─' in text or '│' in text
        if has_borders: width=max(width-4,20)
        lines,curr_line,curr_len=[],[],0
        for w in text.split():
            if has_borders and w.strip('─│╭╮╯╰')=='':
                lines.append(w)
                continue
            if len(w)>width:
                if curr_line: lines.append(' '.join(curr_line))
                lines.extend(w[i:i+width] for i in range(0,len(w),width))
                curr_line,curr_len=[],0
                continue
            wl=len(w)+(1 if curr_len else 0)
            if curr_len+wl<=width:
                curr_line.append(w)
                curr_len+=wl
            else:
                lines.append(' '.join(curr_line))
                curr_line,curr_len=[w],len(w)
        if curr_line: lines.append(' '.join(curr_line))
        return lines

    def split_into_styled_words(self, text:str)->List[dict]:
        words=[]; curr={'word':[],'styled':[],'patterns':[]}
        for i,ch in enumerate(text):
            if ch in self.start_map:
                pat=self.start_map[ch]
                curr['patterns'].append(pat.name)
                if not pat.remove_delimiters:
                    curr['word'].append(ch); curr['styled'].append(ch)
            elif curr['patterns'] and ch in self.end_map:
                pat=self.by_name[curr['patterns'][-1]]
                if ch==pat.end:
                    if not pat.remove_delimiters:
                        curr['word'].append(ch); curr['styled'].append(ch)
                    curr['patterns'].pop()
            elif ch.isspace():
                if curr['word']:
                    words.append({
                        'raw_text':''.join(curr['word']),
                        'styled_text':''.join(curr['styled']),
                        'active_patterns':curr['patterns'].copy()
                    }); curr={'word':[],'styled':[],'patterns':[]}
            else:
                curr['word'].append(ch); curr['styled'].append(ch)
        if curr['word']:
            words.append({
                'raw_text':''.join(curr['word']),
                'styled_text':''.join(curr['styled']),
                'active_patterns':curr['patterns'].copy()
            })
        return words

    def format_styled_lines(self, lines:List[List[dict]], base_color:str)->str:
        res=[]; curr_style=self.get_format('RESET')+base_color
        for line in lines:
            c=[curr_style]
            for w in line:
                s=self.get_style(w['active_patterns'], base_color)
                if s!=curr_style: c.append(s); curr_style=s
                c.append(w['styled_text']+" ")
            f="".join(c).rstrip()
            if f: res.append(f)
        extra=self.get_format('RESET')+base_color
        return "\n".join(res)+(extra if curr_style!=extra else "")

class Stream:
    def __init__(self, styles: Styles, terminal=None):
        self.styles = styles
        self.terminal = terminal
        self._base_color = self.styles.get_format('RESET')
        self.active_patterns = []
        self.current_line_length = 0
        self.word_buffer = ""
        self._buffer_lock = asyncio.Lock()
        self._rich_console = Console(
            force_terminal=True,
            color_system="truecolor",
            file=StringIO(),
            highlight=False
        )

    def set_base_color(self, color: Optional[str] = None):
        if color: self._base_color = self.styles.get_color(color)
        else: self._base_color = self.styles.get_format('RESET')

    def _style_chunk(self, text: str) -> str:
        if not text: return ""
        if any(c in text for c in "╭╮╯╰│"): return text
        out = []
        if not self.active_patterns:
            out.append(
                f"{self.styles.get_format('ITALIC_OFF')}"
                f"{self.styles.get_format('BOLD_OFF')}{self._base_color}"
            )
        for i, ch in enumerate(text):
            if i == 0 or text[i-1].isspace():
                out.append(self.styles.get_style(self.active_patterns, self._base_color))
            if (self.active_patterns and ch in self.styles.end_map
                    and ch == self.styles.by_name[self.active_patterns[-1]].end):
                pat = self.styles.by_name[self.active_patterns[-1]]
                if not pat.remove_delimiters:
                    out.append(self.styles.get_style(self.active_patterns, self._base_color) + ch)
                self.active_patterns.pop()
                out.append(self.styles.get_style(self.active_patterns, self._base_color))
                continue
            if ch in self.styles.start_map:
                new_pat = self.styles.start_map[ch]
                self.active_patterns.append(new_pat.name)
                out.append(self.styles.get_style(self.active_patterns, self._base_color))
                if not new_pat.remove_delimiters: out.append(ch)
                continue
            out.append(ch)
        return "".join(out)

    async def add(self, chunk: str, output_handler=None) -> Tuple[str, str]:
        if not chunk: return "", ""
        async with self._buffer_lock:
            return self.process_and_write(chunk)

    def process_and_write(self, chunk: str) -> Tuple[str, str]:
        if not chunk: return "", ""
        styled_out = ""
        if self.terminal: self.terminal._hide_cursor()
        try:
            if any(c in chunk for c in "╭╮╯╰│"):
                sys.stdout.write(chunk)
                styled_out = chunk
            else:
                for char in chunk:
                    if char.isspace():
                        if self.word_buffer:
                            styled_word = self._style_chunk(self.word_buffer)
                            sys.stdout.write(styled_word)
                            styled_out += styled_word
                            self.word_buffer = ""
                        sys.stdout.write(char)
                        styled_out += char
                        self.current_line_length = 0 if char == '\n' else self.current_line_length + 1
                    else:
                        self.word_buffer += char
            sys.stdout.flush()
            return chunk, styled_out
        finally:
            if self.terminal: self.terminal._hide_cursor()

    async def flush(self, output_handler=None) -> Tuple[str, str]:
        styled_out = ""
        if self.terminal: self.terminal._hide_cursor()
        try:
            if self.word_buffer:
                styled_word = self._style_chunk(self.word_buffer)
                sys.stdout.write(styled_word)
                styled_out += styled_word
                self.word_buffer = ""
            if self.current_line_length > 0:
                sys.stdout.write("\n")
                styled_out += "\n"
            sys.stdout.write(self.styles.get_format('RESET'))
            sys.stdout.flush()
            self.reset()
            return "", styled_out
        finally:
            if self.terminal: self.terminal._hide_cursor()

    def reset(self):
        self.active_patterns.clear()
        self.word_buffer = ""
        self.current_line_length = 0