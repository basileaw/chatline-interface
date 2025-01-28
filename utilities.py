# utilities.py

import sys
import shutil
import re
from typing import List, Optional, Dict
from dataclasses import dataclass

# ANSI handling - needed during transition
ANSI_REGEX = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')

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
        # Initialize pattern storage - will be populated by TextProcessor
        self.by_name: Dict[str, Pattern] = {}
        self.start_map: Dict[str, Pattern] = {}
        self.end_map: Dict[str, Pattern] = {}

    def get_format(self, name: str) -> str:
        """Get format by name from FORMATS dictionary."""
        from state.text import FORMATS
        return FORMATS.get(name, '')

    def get_color(self, name: str) -> str:
        """Get color by name from COLORS dictionary."""
        from state.text import COLORS
        return COLORS.get(name, '')

    def get_base_color(self, color_name: str = 'GREEN') -> str:
        """Get the base color code."""
        from state.text import COLORS
        return COLORS[color_name]

    def get_style(self, active_patterns: List[str], base_color: str) -> str:
        """Get current ANSI style based on active patterns."""
        from state.text import FORMATS, COLORS
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