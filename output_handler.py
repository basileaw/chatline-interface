# output_handler.py
from dataclasses import dataclass
from typing import Optional, List, Dict
import sys

# ANSI Format Codes
FORMATS = {
    'RESET': '\033[0m',
    'ITALIC_ON': '\033[3m',
    'ITALIC_OFF': '\033[23m'
}

# Color Palette
COLORS = {
    'GREEN': '\033[38;5;47m',
    'PINK': '\033[38;5;212m',
    'BLUE': '\033[38;5;75m'
}

@dataclass
class Pattern:
    """Text pattern with associated styling."""
    name: str
    start: str
    end: str
    color: Optional[str]
    italic: bool
    remove_delimiters: bool

class OutputHandler:
    """Handles styling and display of output text."""
    
    def __init__(self, patterns: List[Dict] = None, base_color: str = COLORS['GREEN']):
        self.base_color = base_color
        self.active_patterns = []
        
        default_patterns = [
            {
                'name': 'quotes',
                'start': '"',
                'end': '"',
                'color': COLORS['PINK'],
                'italic': False,
                'remove_delimiters': False
            },
            {
                'name': 'brackets',
                'start': '[',
                'end': ']',
                'color': COLORS['BLUE'],
                'italic': False,
                'remove_delimiters': False
            },
            {
                'name': 'emphasis',
                'start': '_',
                'end': '_',
                'color': None,
                'italic': True,
                'remove_delimiters': True
            }
        ]
        
        self.patterns = [Pattern(**p) for p in (patterns or default_patterns)]
        
        # Validate patterns
        used_chars = set()
        for p in self.patterns:
            if p.start in used_chars or p.end in used_chars:
                raise ValueError(f"Pattern '{p.name}' uses a character that's already in use")
            used_chars.update([p.start, p.end])
        
        # Pattern lookups
        self.by_name = {p.name: p for p in self.patterns}
        self.start_map = {p.start: p for p in self.patterns}
        self.end_map = {p.end: p for p in self.patterns}
    
    def get_style(self) -> str:
        """Get current ANSI style based on active patterns."""
        color = self.base_color
        italic = False
        for name in self.active_patterns:
            p = self.by_name[name]
            if p.color: color = p.color
            if p.italic: italic = True
        return (FORMATS['ITALIC_ON'] if italic else FORMATS['ITALIC_OFF']) + color

    def process_chunk(self, chunk: str) -> str:
        """Process a chunk and return styled text."""
        if not chunk: return ""
        output = []
        i = 0
        
        if not self.active_patterns:
            output.append(FORMATS['ITALIC_OFF'] + self.base_color)
        
        while i < len(chunk):
            ch = chunk[i]
            
            if self.active_patterns and ch in self.end_map and ch == self.by_name[self.active_patterns[-1]].end:
                current_pat = self.by_name[self.active_patterns[-1]]
                if not current_pat.remove_delimiters:
                    output.append(self.get_style() + ch)
                self.active_patterns.pop()
                output.append(self.get_style())
                i += 1
                continue
            
            if ch in self.start_map:
                new_pat = self.start_map[ch]
                self.active_patterns.append(new_pat.name)
                output.append(self.get_style())
                if not new_pat.remove_delimiters:
                    output.append(ch)
                i += 1
                continue
            
            output.append(ch)
            i += 1
        
        return "".join(output)

    def process_and_write(self, chunk: str) -> tuple[str, str]:
        """Process a chunk, write to stdout, and return both raw and styled text."""
        styled_text = self.process_chunk(chunk)
        sys.stdout.write(styled_text)
        sys.stdout.flush()
        return chunk, styled_text

class RawOutputHandler:
    """Simple output handler that writes raw text without styling."""
    
    def __init__(self):
        pass
    
    def process_and_write(self, chunk: str) -> tuple[str, str]:
        """Write raw text to stdout and return both raw and styled versions (same in this case)."""
        sys.stdout.write(chunk)
        sys.stdout.flush()
        return chunk, chunk

