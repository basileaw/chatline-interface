# styles/definition.py

from dataclasses import dataclass
from typing import Dict, List, Optional

FMT = lambda x: f'\033[{x}m'  # Core formatting utility

FORMATS = {
    'RESET': FMT('0'),
    'ITALIC_ON': FMT('3'),
    'ITALIC_OFF': FMT('23'),
    'BOLD_ON': FMT('1'),
    'BOLD_OFF': FMT('22')
}

COLORS = {
    'GREEN': {'ansi': '\033[38;5;47m', 'rich': 'green3'},
    'PINK':  {'ansi': '\033[38;5;212m', 'rich': 'pink1'},
    'BLUE':  {'ansi': '\033[38;5;75m', 'rich': 'blue1'},
    'GRAY':  {'ansi': '\033[38;5;245m', 'rich': 'gray50'},
    'YELLOW': {'ansi': '\033[38;5;227m', 'rich': 'yellow1'},
    'WHITE': {'ansi': '\033[38;5;255m', 'rich': 'white'}
}

BOX_CHARS = {'─', '│', '╭', '╮', '╯', '╰'}

@dataclass
class Pattern:
    """Defines a text styling pattern."""
    name: str
    start: str
    end: str
    color: Optional[str] = None
    styles: Optional[List[str]] = None
    remove_delimiters: bool = False

@dataclass
class StyleDefinitions:
    """Container for style configurations."""
    formats: Dict[str, str]
    colors: Dict[str, Dict[str, str]]
    box_chars: set
    patterns: Dict[str, Pattern]
    
    @classmethod
    def create_default_patterns(cls) -> Dict[str, Pattern]:
        """Return the default text styling patterns."""
        base_patterns = {
            'quotes': {'start': '"', 'end': '"', 'color': 'PINK'},
            'brackets': {'start': '[', 'end': ']', 'color': 'GRAY', 'styles': ['ITALIC'], 'remove_delimiters': True},
            'emphasis': {'start': '_', 'end': '_', 'color': None, 'styles': ['ITALIC'], 'remove_delimiters': True},
            'strong': {'start': '*', 'end': '*', 'color': None, 'styles': ['BOLD'], 'remove_delimiters': True}
        }
        # Update the first pattern to have no styles and keep delimiters.
        base_patterns.update({k: {**v, 'styles': [], 'remove_delimiters': False}
                              for k, v in list(base_patterns.items())[:1]})
        patterns = {}
        used_delimiters = set()
        for name, cfg in base_patterns.items():
            pattern = Pattern(name=name, **cfg)
            if pattern.start in used_delimiters or pattern.end in used_delimiters:
                raise ValueError(f"Duplicate delimiter in pattern '{pattern.name}'")
            used_delimiters.update([pattern.start, pattern.end])
            patterns[name] = pattern
        return patterns

DEFAULT_DEFINITIONS = StyleDefinitions(
    formats=FORMATS,
    colors=COLORS,
    box_chars=BOX_CHARS,
    patterns=StyleDefinitions.create_default_patterns()
)
