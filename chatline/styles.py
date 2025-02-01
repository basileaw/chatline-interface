# styles.py

import re
from typing import List, Optional, Dict
from dataclasses import dataclass
from rich.style import Style
from rich.color import Color

ANSI_REGEX = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
FMT = lambda x: f'\033[{x}m'
FORMATS = {
    'RESET': FMT('0'),
    'ITALIC_ON': FMT('3'),
    'ITALIC_OFF': FMT('23'),
    'BOLD_ON': FMT('1'),
    'BOLD_OFF': FMT('22')
}

# Map our ANSI colors to Rich-compatible colors
COLORS = {
    'GREEN': {'ansi': f'\033[38;5;47m', 'rich': 'green3'},
    'PINK': {'ansi': f'\033[38;5;212m', 'rich': 'pink1'},
    'BLUE': {'ansi': f'\033[38;5;75m', 'rich': 'blue1'}
}

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

class Styles:
    def __init__(self):
        self.by_name = {}
        self.start_map = {}
        self.end_map = {}
        used = set()
        
        # Initialize pattern mappings
        for name, cfg in STYLE_PATTERNS.items():
            if (pat := Pattern(name=name, **cfg)).start in used or pat.end in used:
                raise ValueError(f"Duplicate delimiter in '{pat.name}'")
            used.update([pat.start, pat.end])
            self.by_name[name] = self.start_map[pat.start] = self.end_map[pat.end] = pat
            
        # Initialize Rich style mappings
        self.rich_styles = {
            name: Style(color=color['rich']) 
            for name, color in COLORS.items()
        }

    def get_format(self, name: str) -> str:
        return FORMATS.get(name, '')

    def get_color(self, name: str) -> str:
        return COLORS.get(name, {}).get('ansi', '')

    def get_rich_style(self, name: str) -> Style:
        """Get Rich-compatible style for a color name."""
        return self.rich_styles.get(name, Style())

    def get_base_color(self, color_name: str = 'GREEN') -> str:
        return COLORS.get(color_name, {}).get('ansi', '')

    def get_visible_length(self, text: str) -> int:
        """Get visible length of text, ignoring ANSI and Rich styling."""
        # First strip ANSI
        text = ANSI_REGEX.sub('', text)
        # Then strip Rich box characters if present
        text = text.replace('─', '').replace('│', '').replace('╭', '') \
                   .replace('╮', '').replace('╯', '').replace('╰', '')
        return len(text)

    def get_style(self, active_patterns: List[str], base_color: str) -> str:
        style = [base_color]
        for name in active_patterns:
            if (pat := self.by_name[name]).color:
                style[0] = COLORS[pat.color]['ansi']
            style.extend(FORMATS[f'{s}_ON'] for s in pat.styles or [])
        return ''.join(style)

    def split_text(self, text: str, width: Optional[int] = None) -> List[str]:
        if width is None:
            width = 80  # Default terminal width
        
        # Handle text that might contain Rich panel borders
        has_borders = '─' in text or '│' in text
        
        # Adjust width for panel borders if needed
        if has_borders:
            width = max(width - 4, 20)  # Account for left/right borders and padding
            
        lines, curr_line, curr_len = [], [], 0
        
        for word in text.split():
            # Skip panel border characters
            if has_borders and word.strip('─│╭╮╯╰') == '':
                lines.append(word)
                continue
                
            if len(word) > width:
                if curr_line:
                    lines.append(' '.join(curr_line))
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
        
        if curr_line:
            lines.append(' '.join(curr_line))
        return lines

    def split_into_styled_words(self, text: str) -> List[dict]:
        words, curr = [], {'word': [], 'styled': [], 'patterns': []}
        
        for i, char in enumerate(text):
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