from dataclasses import dataclass
from typing import Optional, List, Dict

# Keep FORMATS and COLORS exactly where they are
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

# Define patterns but keep exact same behavior
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

class TextPainter:
    def __init__(self, utilities, base_color='GREEN'):
        self.utils = utilities
        self._base_color = COLORS[base_color]
        self.active_patterns: List[str] = []
        
        # Convert style patterns to Pattern objects
        self.patterns = []
        for name, config in STYLE_PATTERNS.items():
            self.patterns.append(Pattern(
                name=name,
                start=config['start'],
                end=config['end'],
                color=config['color'],  # Store name, not code
                styles=config['styles'],
                remove_delimiters=config['remove_delimiters']
            ))

        # Keep exact same validation
        used = set()
        for p in self.patterns:
            if p.start in used or p.end in used:
                raise ValueError(f"Duplicate delimiter in '{p.name}'")
            used.update([p.start, p.end])

        self.by_name = {p.name: p for p in self.patterns}
        self.start_map = {p.start: p for p in self.patterns}
        self.end_map = {p.end: p for p in self.patterns}

    def get_format(self, name: str) -> str:
        """Get format by name from FORMATS dictionary."""
        return FORMATS.get(name, '')

    def get_color(self, name: str) -> str:
        """Get color by name from COLORS dictionary."""
        return COLORS.get(name, '')

    @property
    def base_color(self) -> str:
        return self._base_color

    def get_style(self) -> str:
        """Get current ANSI style based on active patterns."""
        color = self.base_color
        style_codes = []
        
        for name in self.active_patterns:
            pat = self.by_name[name]
            if pat.color:
                color = COLORS[pat.color]
            for style in pat.styles:
                style_codes.append(FORMATS[f'{style}_ON'])
                
        return color + ''.join(style_codes)

    def process_chunk(self, text: str) -> str:
        """Process a chunk of text and apply ANSI styling."""
        if not text:
            return ""
            
        out, i = [], 0
        
        if not self.active_patterns:
            out.append(FORMATS['ITALIC_OFF'] + FORMATS['BOLD_OFF'] + self.base_color)
            
        while i < len(text):
            ch = text[i]
            
            if i == 0 or text[i-1].isspace():
                out.append(self.get_style())
                
            if self.active_patterns and ch in self.end_map:
                if ch == self.by_name[self.active_patterns[-1]].end:
                    pat = self.by_name[self.active_patterns[-1]]
                    if not pat.remove_delimiters:
                        out.append(self.get_style() + ch)
                    self.active_patterns.pop()
                    out.append(self.get_style())
                    i += 1
                    continue
                    
            if ch in self.start_map:
                new_pat = self.start_map[ch]
                self.active_patterns.append(new_pat.name)
                out.append(self.get_style())
                if not new_pat.remove_delimiters:
                    out.append(ch)
                i += 1
                continue
                
            out.append(ch)
            i += 1
            
        return "".join(out)

    def reset(self) -> None:
        """Reset all active patterns."""
        self.active_patterns.clear()