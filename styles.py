# styles.py

from dataclasses import dataclass
from typing import Optional, List, Dict

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

def get_format(name: str) -> str:
    """Get format by name from FORMATS dictionary."""
    return FORMATS.get(name, '')

def get_color(name: str) -> str:
    """Get color by name from COLORS dictionary."""
    return COLORS.get(name, '')

def get_base_color(color_name: str = 'GREEN') -> str:
    """Get the base color code."""
    return COLORS[color_name]

def get_style(active_patterns: List[str], base_color: str, patterns_map: Dict[str, Pattern]) -> str:
    """Get current ANSI style based on active patterns."""
    color = base_color
    style_codes = []
    
    for name in active_patterns:
        pat = patterns_map[name]
        if pat.color:
            color = COLORS[pat.color]
        for style in pat.styles:
            style_codes.append(FORMATS[f'{style}_ON'])
            
    return color + ''.join(style_codes)

def validate_patterns() -> tuple[Dict[str, Pattern], Dict[str, Pattern], Dict[str, Pattern]]:
    """Validate and convert style patterns to Pattern objects."""
    patterns = []
    for name, config in STYLE_PATTERNS.items():
        patterns.append(Pattern(
            name=name,
            start=config['start'],
            end=config['end'],
            color=config['color'],
            styles=config['styles'],
            remove_delimiters=config['remove_delimiters']
        ))

    # Validate no duplicate delimiters
    used = set()
    for p in patterns:
        if p.start in used or p.end in used:
            raise ValueError(f"Duplicate delimiter in '{p.name}'")
        used.update([p.start, p.end])

    # Create lookup maps
    by_name = {p.name: p for p in patterns}
    start_map = {p.start: p for p in patterns}
    end_map = {p.end: p for p in patterns}
    
    return by_name, start_map, end_map