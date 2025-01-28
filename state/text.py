# state/text.py
import sys, asyncio, re
from typing import List, Optional, Tuple, Dict
from dataclasses import dataclass

# ANSI handling
ANSI_REGEX = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')

# Style constants
FORMATS = {
    'RESET': '\033[0m',
    'ITALIC_ON': '\033[3m',
    'ITALIC_OFF': '\033[23m',
    'BOLD_ON': '\033[1m',
    'BOLD_OFF': '\033[22m'
}

COLORS = {
    'GREEN': '\033[38;5;47m',
    'PINK': '\033[38;5;212m',
    'BLUE': '\033[38;5;75m'
}

STYLE_PATTERNS = {
    'quotes': {
        'start': '"',
        'end': '"',
        'color': 'PINK',
        'styles': [],
        'remove_delimiters': False
    },
    'brackets': {
        'start': '[',
        'end': ']',
        'color': 'BLUE',
        'styles': [],
        'remove_delimiters': False
    },
    'emphasis': {
        'start': '_',
        'end': '_',
        'color': None,
        'styles': ['ITALIC'],
        'remove_delimiters': True
    },
    'strong': {
        'start': '*',
        'end': '*',
        'color': None,
        'styles': ['BOLD'],
        'remove_delimiters': True
    }
}

@dataclass
class Pattern:
    name: str
    start: str
    end: str
    color: Optional[str]
    styles: List[str]
    remove_delimiters: bool

class TextProcessor:
    def __init__(self, utilities):
        self.utils = utilities
        
        # Initialize and validate patterns
        self.patterns = []
        used = set()
        
        for name, config in STYLE_PATTERNS.items():
            pattern = Pattern(
                name=name,
                start=config['start'],
                end=config['end'],
                color=config['color'],
                styles=config['styles'],
                remove_delimiters=config['remove_delimiters']
            )
            
            # Validate no duplicate delimiters
            if pattern.start in used or pattern.end in used:
                raise ValueError(f"Duplicate delimiter in '{pattern.name}'")
            used.update([pattern.start, pattern.end])
            
            self.patterns.append(pattern)
            
            # Set in utilities for transition period
            self.utils.by_name[name] = pattern
            self.utils.start_map[pattern.start] = pattern
            self.utils.end_map[pattern.end] = pattern

        # Create our own lookup maps
        self.by_name = {p.name: p for p in self.patterns}
        self.start_map = {p.start: p for p in self.patterns}
        self.end_map = {p.end: p for p in self.patterns}

    def create_styled_handler(self) -> 'StyledTextHandler':
        return StyledTextHandler(self.utils)

    def get_format(self, name: str) -> str:
        return FORMATS.get(name, '')

    def get_color(self, name: str) -> str:
        return COLORS.get(name, '')

    def get_base_color(self, color_name: str = 'GREEN') -> str:
        return COLORS[color_name]

    def get_style(self, active_patterns: List[str], base_color: str) -> str:
        color = base_color
        style_codes = []
        for name in active_patterns:
            pat = self.by_name[name]
            if pat.color:
                color = COLORS[pat.color]
            for style in pat.styles:
                style_codes.append(FORMATS[f'{style}_ON'])
        return color + ''.join(style_codes)

    def get_visible_length(self, text: str) -> int:
        return len(ANSI_REGEX.sub('', text))

    def split_into_display_lines(self, text: str, width: Optional[int] = None) -> List[str]:
        if width is None:
            width = self.utils.get_terminal_width()
        lines = []
        words = text.split()
        current_line, current_length = [], 0
        for word in words:
            word_length = len(word) + (1 if current_length > 0 else 0)
            if current_length + word_length <= width:
                current_line.append(word)
                current_length += word_length
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
                current_length = len(word)
        if current_line:
            lines.append(' '.join(current_line))
        return lines

    def handle_long_word(self, word: str, width: Optional[int] = None) -> List[str]:
        if width is None:
            width = self.utils.get_terminal_width()
        chunks = []
        while word:
            if len(word) <= width:
                chunks.append(word)
                break
            chunks.append(word[:width])
            word = word[width:]
        return chunks

    def split_into_styled_words(self, text: str, patterns: dict) -> List[dict]:
        words, current = [], {'word': [], 'styled': [], 'patterns': []}
        i = 0
        while i < len(text):
            char = text[i]
            if char in patterns['start_map']:
                pattern = patterns['start_map'][char]
                current['patterns'].append(pattern.name)
                if not pattern.remove_delimiters:
                    current['word'].append(char)
                    current['styled'].append(char)
            elif current['patterns'] and char in patterns['end_map']:
                pattern = patterns['by_name'][current['patterns'][-1]]
                if char == pattern.end:
                    if not pattern.remove_delimiters:
                        current['word'].append(char)
                        current['styled'].append(char)
                    current['patterns'].pop()
            elif char.isspace():
                if current['word']:
                    words.append({
                        'raw_text': ''.join(current['word']),
                        'styled_text': ''.join(current['styled']),
                        'active_patterns': current['patterns'].copy()
                    })
                    current = {'word': [], 'styled': [], 'patterns': []}
            else:
                current['word'].append(char)
                current['styled'].append(char)
            i += 1
        if current['word']:
            words.append({
                'raw_text': ''.join(current['word']),
                'styled_text': ''.join(current['styled']),
                'active_patterns': current['patterns'].copy()
            })
        return words

    def format_styled_lines(self, lines: List[List[dict]], base_color: str) -> str:
        formatted_lines, current_style = [], self.utils.get_format('RESET') + base_color
        for line in lines:
            line_content = [current_style]
            for word in line:
                new_style = self.utils.get_style(word['active_patterns'], base_color)
                if new_style != current_style:
                    line_content.append(new_style)
                    current_style = new_style
                line_content.append(word['styled_text'] + " ")
            formatted_line = "".join(line_content).rstrip()
            if formatted_line: formatted_lines.append(formatted_line)
        result = "\n".join(formatted_lines)
        if current_style != self.utils.get_format('RESET') + base_color:
            result += self.utils.get_format('RESET') + base_color
        return result


class StyledTextHandler:
    def __init__(self, utilities):
        self.utils = utilities
        self._base_color = utilities.get_base_color('GREEN')
        self.active_patterns, self.current_line_length = [], 0
        self.word_buffer = ""
        self._buffer_lock = asyncio.Lock()
        self.by_name = utilities.by_name
        self.start_map, self.end_map = utilities.start_map, utilities.end_map

    def _process_chunk(self, text: str) -> str:
        if not text: return ""
        out, i = [], 0
        if not self.active_patterns:
            out.append(self.utils.get_format('ITALIC_OFF') + 
                      self.utils.get_format('BOLD_OFF') + self._base_color)
        while i < len(text):
            ch = text[i]
            if i == 0 or text[i-1].isspace():
                out.append(self.utils.get_style(self.active_patterns, self._base_color))
            if self.active_patterns and ch in self.end_map and ch == self.by_name[self.active_patterns[-1]].end:
                pat = self.by_name[self.active_patterns[-1]]
                if not pat.remove_delimiters:
                    out.append(self.utils.get_style(self.active_patterns, self._base_color) + ch)
                self.active_patterns.pop()
                out.append(self.utils.get_style(self.active_patterns, self._base_color))
                i += 1; continue
            if ch in self.start_map:
                new_pat = self.start_map[ch]
                self.active_patterns.append(new_pat.name)
                out.append(self.utils.get_style(self.active_patterns, self._base_color))
                if not new_pat.remove_delimiters: out.append(ch)
                i += 1; continue
            out.append(ch)
            i += 1
        return "".join(out)

    def process_and_write(self, chunk: str) -> Tuple[str, str]:
        if not chunk: return ("", "")
        width = self.utils.get_terminal_width()
        raw_out, styled_out = chunk, ""
        i = 0
        while i < len(chunk):
            char = chunk[i]
            if char.isspace():
                if self.word_buffer:
                    word_length = self.utils.get_visible_length(self.word_buffer)
                    if word_length > width:
                        word_chunks = self.utils.handle_long_word(self.word_buffer, width)
                        for idx, word_chunk in enumerate(word_chunks):
                            if idx > 0:
                                self.utils.write_and_flush("\n")
                                styled_out += "\n"
                                self.current_line_length = 0
                            styled_chunk = self._process_chunk(word_chunk)
                            self.utils.write_and_flush(styled_chunk)
                            styled_out += styled_chunk
                            self.current_line_length = len(word_chunk)
                    else:
                        if self.current_line_length + word_length > width:
                            self.utils.write_and_flush("\n")
                            styled_out += "\n"
                            self.current_line_length = 0
                        styled_word = self._process_chunk(self.word_buffer)
                        self.utils.write_and_flush(styled_word)
                        styled_out += styled_word
                        self.current_line_length += word_length
                    self.word_buffer = ""
                if char == '\n':
                    self.utils.write_and_flush("\n")
                    styled_out += "\n"
                    self.current_line_length = 0
                elif self.current_line_length + 1 <= width:
                    self.utils.write_and_flush(char)
                    styled_out += char
                    self.current_line_length += 1
            else: self.word_buffer += char
            i += 1
        sys.stdout.flush()
        return (raw_out, styled_out)

    async def add(self, chunk: str, output_handler=None) -> Tuple[str, str]:
        if not chunk: return "", ""
        async with self._buffer_lock:
            return self.process_and_write(chunk)

    async def flush(self, output_handler=None) -> Tuple[str, str]:
        styled_out = ""
        if self.word_buffer:
            width = self.utils.get_terminal_width()
            word_length = self.utils.get_visible_length(self.word_buffer)
            if word_length > width:
                for idx, chunk in enumerate(self.utils.handle_long_word(self.word_buffer, width)):
                    if idx > 0:
                        self.utils.write_and_flush("\n")
                        styled_out += "\n"
                    styled_chunk = self._process_chunk(chunk)
                    self.utils.write_and_flush(styled_chunk)
                    styled_out += styled_chunk
            else:
                if self.current_line_length + word_length > width:
                    self.utils.write_and_flush("\n")
                    styled_out += "\n"
                styled_word = self._process_chunk(self.word_buffer)
                self.utils.write_and_flush(styled_word)
                styled_out += styled_word
            self.word_buffer = ""
        if self.current_line_length > 0:
            self.utils.write_and_flush("\n")
            styled_out += "\n"
        self.utils.write_and_flush(self.utils.get_format('RESET'))
        sys.stdout.flush()
        self.reset()
        return "", styled_out

    def reset(self) -> None:
        self.active_patterns.clear()
        self.word_buffer = ""
        self.current_line_length = 0