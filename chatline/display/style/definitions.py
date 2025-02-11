# style/definitions.py

from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class Pattern:
    """Defines a text styling pattern."""
    name: str
    start: str
    end: str
    color: Optional[str] = None
    style: Optional[List[str]] = None
    remove_delimiters: bool = False

class StyleDefinitions:
    """Container for style configurations."""
    
    # Default formatting utility
    FMT = lambda x: f'\033[{x}m'
    
    # Class-level defaults
    DEFAULT_FORMATS = {
        'RESET': FMT('0'),
        'ITALIC_ON': FMT('3'),
        'ITALIC_OFF': FMT('23'),
        'BOLD_ON': FMT('1'),
        'BOLD_OFF': FMT('22')
    }

    DEFAULT_COLORS = {
        'GREEN': {'ansi': '\033[38;5;47m', 'rich': 'green3'},
        'PINK':  {'ansi': '\033[38;5;212m', 'rich': 'pink1'},
        'BLUE':  {'ansi': '\033[38;5;75m', 'rich': 'blue1'},
        'GRAY':  {'ansi': '\033[38;5;245m', 'rich': 'gray50'},
        'YELLOW': {'ansi': '\033[38;5;227m', 'rich': 'yellow1'},
        'WHITE': {'ansi': '\033[38;5;255m', 'rich': 'white'}
    }

    DEFAULT_BOX_CHARS = {'─', '│', '╭', '╮', '╯', '╰'}

    def __init__(
        self,
        formats: Optional[Dict[str, str]] = None,
        colors: Optional[Dict[str, Dict[str, str]]] = None,
        box_chars: Optional[set] = None,
        patterns: Optional[Dict[str, Pattern]] = None
    ):
        """Initialize style definitions with optional custom configurations."""
        self.formats = formats if formats is not None else self.DEFAULT_FORMATS.copy()
        self.colors = colors if colors is not None else self.DEFAULT_COLORS.copy()
        self.box_chars = box_chars if box_chars is not None else self.DEFAULT_BOX_CHARS.copy()
        self.patterns = patterns if patterns is not None else self._create_default_patterns()

    def _create_default_patterns(self) -> Dict[str, Pattern]:
        """Create the default text styling patterns."""
        base_patterns = {
            'quotes': {'start': '"', 'end': '"', 'color': 'PINK'},
            'brackets': {'start': '[', 'end': ']', 'color': 'GRAY', 'style': ['ITALIC'], 'remove_delimiters': True},
            'emphasis': {'start': '_', 'end': '_', 'color': None, 'style': ['ITALIC'], 'remove_delimiters': True},
            'strong': {'start': '*', 'end': '*', 'color': None, 'style': ['BOLD'], 'remove_delimiters': True}
        }
        
        # Update the first pattern to have no style and keep delimiters
        base_patterns.update({k: {**v, 'style': [], 'remove_delimiters': False}
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

    def get_format(self, name: str) -> str:
        """Get a format by name."""
        return self.formats.get(name, '')

    def get_color(self, name: str) -> Dict[str, str]:
        """Get a color configuration by name."""
        return self.colors.get(name, {'ansi': '', 'rich': ''})

    def get_pattern(self, name: str) -> Optional[Pattern]:
        """Get a pattern by name."""
        return self.patterns.get(name)

    def add_pattern(self, pattern: Pattern) -> None:
        """Add a new pattern to the definitions."""
        if pattern.name in self.patterns:
            raise ValueError(f"Pattern '{pattern.name}' already exists")
        if any(p.start == pattern.start or p.end == pattern.end for p in self.patterns.values()):
            raise ValueError(f"Pattern delimiters for '{pattern.name}' conflict with existing patterns")
        self.patterns[pattern.name] = pattern