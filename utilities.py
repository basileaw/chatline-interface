# utilities.py

import sys
import shutil
import re
from typing import List, Optional, Dict
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

class RealUtilities:
    def __init__(self):
        # Initialize and validate patterns
        self.patterns = []
        for name, config in STYLE_PATTERNS.items():
            self.patterns.append(Pattern(
                name=name,
                start=config['start'],
                end=config['end'],
                color=config['color'],
                styles=config['styles'],
                remove_delimiters=config['remove_delimiters']
            ))

        # Validate no duplicate delimiters
        used = set()
        for p in self.patterns:
            if p.start in used or p.end in used:
                raise ValueError(f"Duplicate delimiter in '{p.name}'")
            used.update([p.start, p.end])

        # Create lookup maps
        self.by_name = {p.name: p for p in self.patterns}
        self.start_map = {p.start: p for p in self.patterns}
        self.end_map = {p.end: p for p in self.patterns}

    def get_format(self, name: str) -> str:
        """Get format by name from FORMATS dictionary."""
        return FORMATS.get(name, '')

    def get_color(self, name: str) -> str:
        """Get color by name from COLORS dictionary."""
        return COLORS.get(name, '')

    def get_base_color(self, color_name: str = 'GREEN') -> str:
        """Get the base color code."""
        return COLORS[color_name]

    def get_style(self, active_patterns: List[str], base_color: str) -> str:
        """Get current ANSI style based on active patterns."""
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
        """Get visible length of text, ignoring ANSI escape codes."""
        return len(ANSI_REGEX.sub('', text))

    def get_terminal_width(self) -> int:
        """Get current terminal width."""
        return shutil.get_terminal_size().columns

    def show_cursor(self) -> None:
        """Show the terminal cursor."""
        if sys.stdout.isatty():
            sys.stdout.write("\033[?25h")
            sys.stdout.flush()

    def hide_cursor(self) -> None:
        """Hide the terminal cursor."""
        if sys.stdout.isatty():
            sys.stdout.write("\033[?25l")
            sys.stdout.flush()

    def clear_screen(self) -> None:
        """Clear the terminal screen and reset cursor position."""
        if sys.stdout.isatty():
            sys.stdout.write("\033[2J\033[H")
            sys.stdout.flush()

    def write_and_flush(self, text: str) -> None:
        """Write text to stdout and flush buffer."""
        sys.stdout.write(text)
        sys.stdout.flush()

    def split_into_display_lines(self, text: str, width: Optional[int] = None) -> List[str]:
        """Split text into lines that fit within terminal width."""
        if width is None:
            width = self.get_terminal_width()
            
        display_lines = []
        words = text.split()
        current_line = []
        current_length = 0
        
        for word in words:
            word_length = len(word) + (1 if current_length > 0 else 0)
            if current_length + word_length <= width:
                current_line.append(word)
                current_length += word_length
            else:
                if current_line:
                    display_lines.append(' '.join(current_line))
                current_line = [word]
                current_length = len(word)
        
        if current_line:
            display_lines.append(' '.join(current_line))
        return display_lines

    def handle_long_word(self, word: str, width: Optional[int] = None) -> List[str]:
        """Split a word that exceeds terminal width into chunks."""
        if width is None:
            width = self.get_terminal_width()
            
        chunks = []
        while word:
            if len(word) <= width:
                chunks.append(word)
                break
            chunks.append(word[:width])
            word = word[width:]
        return chunks

# Legacy function wrappers for backward compatibility
def get_visible_length(text: str) -> int:
    return RealUtilities().get_visible_length(text)

def get_terminal_width() -> int:
    return RealUtilities().get_terminal_width()

def show_cursor() -> None:
    RealUtilities().show_cursor()

def hide_cursor() -> None:
    RealUtilities().hide_cursor()

def manage_cursor(show: bool) -> None:
    if show:
        RealUtilities().show_cursor()
    else:
        RealUtilities().hide_cursor()

def clear_screen() -> None:
    RealUtilities().clear_screen()

def write_and_flush(text: str) -> None:
    RealUtilities().write_and_flush(text)

def split_into_display_lines(text: str, width: Optional[int] = None) -> List[str]:
    return RealUtilities().split_into_display_lines(text, width)

def handle_long_word(word: str, width: Optional[int] = None) -> List[str]:
    return RealUtilities().handle_long_word(word, width)