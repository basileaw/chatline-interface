# text.py

import sys, asyncio, re
from typing import List, Optional, Tuple, Dict
from dataclasses import dataclass

ANSI_REGEX = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
FMT = lambda x: f'\033[{x}m'
FORMATS = {'RESET': FMT('0'), 'ITALIC_ON': FMT('3'), 'ITALIC_OFF': FMT('23'), 'BOLD_ON': FMT('1'), 'BOLD_OFF': FMT('22')}
COLORS = {k: f'\033[38;5;{v}m' for k, v in {'GREEN': '47', 'PINK': '212', 'BLUE': '75'}.items()}
STYLE_PATTERNS = {
    'quotes': {'start': '"', 'end': '"', 'color': 'PINK'},
    'brackets': {'start': '[', 'end': ']', 'color': 'BLUE'},
    'emphasis': {'start': '_', 'end': '_', 'color': None, 'styles': ['ITALIC'], 'remove_delimiters': True},
    'strong': {'start': '*', 'end': '*', 'color': None, 'styles': ['BOLD'], 'remove_delimiters': True}
}
STYLE_PATTERNS.update({k: {**v, 'styles': [], 'remove_delimiters': False} for k, v in list(STYLE_PATTERNS.items())[:2]})

@dataclass
class Pattern:
    name: str
    start: str
    end: str
    color: Optional[str]
    styles: List[str] = None
    remove_delimiters: bool = False

class TextProcessor:
    def __init__(self):
        self.by_name = {}
        self.start_map = {}
        self.end_map = {}
        used = set()
        
        for name, cfg in STYLE_PATTERNS.items():
            if (pat := Pattern(name=name, **cfg)).start in used or pat.end in used:
                raise ValueError(f"Duplicate delimiter in '{pat.name}'")
            used.update([pat.start, pat.end])
            self.by_name[name] = self.start_map[pat.start] = self.end_map[pat.end] = pat

    def create_styled_handler(self) -> 'StyledTextHandler':
        return StyledTextHandler(self)

    def get_format(self, name: str) -> str: return FORMATS.get(name, '')
    def get_color(self, name: str) -> str: return COLORS.get(name, '')
    def get_base_color(self, color_name: str = 'GREEN') -> str: return COLORS[color_name]
    def get_visible_length(self, text: str) -> int: return len(ANSI_REGEX.sub('', text))

    def get_style(self, active_patterns: List[str], base_color: str) -> str:
        style = [base_color]
        for name in active_patterns:
            if (pat := self.by_name[name]).color:
                style[0] = COLORS[pat.color]
            style.extend(FORMATS[f'{s}_ON'] for s in pat.styles or [])
        return ''.join(style)

    def split_text(self, text: str, width: Optional[int] = None) -> List[str]:
        if width is None: width = self.get_terminal_width()
        lines, curr_line, curr_len = [], [], 0
        
        for word in text.split():
            if len(word) > width:
                if curr_line: lines.append(' '.join(curr_line))
                lines.extend(word[i:i+width] for i in range(0, len(word), width))
                curr_line, curr_len = [], 0
                continue
            
            word_len = len(word) + bool(curr_len)
            if curr_len + word_len <= width:
                curr_line.append(word)
                curr_len += word_len
            else:
                lines.append(' '.join(curr_line))
                curr_line, curr_len = [word], len(word)
        
        if curr_line: lines.append(' '.join(curr_line))
        return lines

    def split_into_styled_words(self, text: str, patterns: dict) -> List[dict]:
        words, curr = [], {'word': [], 'styled': [], 'patterns': []}
        
        for i, char in enumerate(text):
            if char in patterns['start_map']:
                pat = patterns['start_map'][char]
                curr['patterns'].append(pat.name)
                if not pat.remove_delimiters:
                    curr['word'].append(char)
                    curr['styled'].append(char)
            elif curr['patterns'] and char in patterns['end_map']:
                pat = patterns['by_name'][curr['patterns'][-1]]
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

    def format_styled_lines(self, lines: List[List[dict]], base_color: str) -> str:
        result = []
        curr_style = self.get_format('RESET') + base_color
        
        for line in lines:
            content = [curr_style]
            for word in line:
                if (new_style := self.get_style(word['active_patterns'], base_color)) != curr_style:
                    content.append(new_style)
                    curr_style = new_style
                content.append(f"{word['styled_text']} ")
            
            if formatted := "".join(content).rstrip():
                result.append(formatted)
        
        return "\n".join(result) + (self.get_format('RESET') + base_color 
                                  if curr_style != self.get_format('RESET') + base_color else "")

class StyledTextHandler:
    def __init__(self, text_processor: TextProcessor):
        self.text_processor = text_processor
        self._base_color = text_processor.get_base_color('GREEN')
        self.active_patterns = []
        self.current_line_length = 0
        self.word_buffer = ""
        self._buffer_lock = asyncio.Lock()
        self.by_name = text_processor.by_name
        self.start_map = text_processor.start_map
        self.end_map = text_processor.end_map

    def _process_chunk(self, text: str) -> str:
        if not text: return ""
        out = []
        if not self.active_patterns:
            out.append(f"{self.text_processor.get_format('ITALIC_OFF')}"
                      f"{self.text_processor.get_format('BOLD_OFF')}{self._base_color}")
        
        for i, ch in enumerate(text):
            if i == 0 or text[i-1].isspace():
                out.append(self.text_processor.get_style(self.active_patterns, self._base_color))
                
            if self.active_patterns and ch in self.end_map and ch == self.by_name[self.active_patterns[-1]].end:
                pat = self.by_name[self.active_patterns[-1]]
                if not pat.remove_delimiters:
                    out.append(f"{self.text_processor.get_style(self.active_patterns, self._base_color)}{ch}")
                self.active_patterns.pop()
                out.append(self.text_processor.get_style(self.active_patterns, self._base_color))
                continue
                
            if ch in self.start_map:
                new_pat = self.start_map[ch]
                self.active_patterns.append(new_pat.name)
                out.append(self.text_processor.get_style(self.active_patterns, self._base_color))
                if not new_pat.remove_delimiters:
                    out.append(ch)
                continue
                
            out.append(ch)
        
        return "".join(out)

    async def add(self, chunk: str, output_handler=None) -> Tuple[str, str]:
        if not chunk: return "", ""
        async with self._buffer_lock:
            return self.process_and_write(chunk)

    def process_and_write(self, chunk: str) -> Tuple[str, str]:
        if not chunk: return ("", "")
        styled_out = ""
        
        for char in chunk:
            if char.isspace():
                if self.word_buffer:
                    styled_word = self._process_chunk(self.word_buffer)
                    sys.stdout.write(styled_word)
                    styled_out += styled_word
                    self.word_buffer = ""
                sys.stdout.write(char)
                styled_out += char
                self.current_line_length = 0 if char == '\n' else self.current_line_length + 1
            else:
                self.word_buffer += char
        
        sys.stdout.flush()
        return (chunk, styled_out)

    async def flush(self, output_handler=None) -> Tuple[str, str]:
        styled_out = ""
        if self.word_buffer:
            styled_word = self._process_chunk(self.word_buffer)
            sys.stdout.write(styled_word)
            styled_out += styled_word
            self.word_buffer = ""

        if self.current_line_length > 0:
            sys.stdout.write("\n")
            styled_out += "\n"
        
        sys.stdout.write(self.text_processor.get_format('RESET'))
        sys.stdout.flush()
        self.reset()
        return "", styled_out

    def reset(self) -> None:
        self.active_patterns.clear()
        self.word_buffer = ""
        self.current_line_length = 0