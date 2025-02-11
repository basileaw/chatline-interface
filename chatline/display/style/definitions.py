# display/style/definitions.py

from dataclasses import dataclass
from typing import Dict, List, Optional, Set

@dataclass
class Pattern:
    """
    Defines a text styling pattern with its formatting rules.
    """
    name: str
    start: str
    end: str
    color: Optional[str] = None
    style: Optional[List[str]] = None
    remove_delimiters: bool = False

class StyleDefinitions:
    """
    Core style definitions container that serves as the foundation layer
    for the styling system. Has no external dependencies.
    """
    
    # ANSI format utility
    FMT = staticmethod(lambda x: f'\033[{x}m')
    
    def __init__(
        self,
        formats: Optional[Dict[str, str]] = None,
        colors: Optional[Dict[str, Dict[str, str]]] = None,
        box_chars: Optional[Set[str]] = None,
        patterns: Optional[Dict[str, Pattern]] = None
    ):
        """
        Initialize style definitions with optional custom configurations.
        """
        # Initialize default formats
        self._default_formats = {
            'RESET': self.FMT('0'),
            'ITALIC_ON': self.FMT('3'),
            'ITALIC_OFF': self.FMT('23'),
            'BOLD_ON': self.FMT('1'),
            'BOLD_OFF': self.FMT('22')
        }
        
        # Initialize default colors
        self._default_colors = {
            'GREEN': {'ansi': '\033[38;5;47m', 'rich': 'green3'},
            'PINK': {'ansi': '\033[38;5;212m', 'rich': 'pink1'},
            'BLUE': {'ansi': '\033[38;5;75m', 'rich': 'blue1'},
            'GRAY': {'ansi': '\033[38;5;245m', 'rich': 'gray50'},
            'YELLOW': {'ansi': '\033[38;5;227m', 'rich': 'yellow1'},
            'WHITE': {'ansi': '\033[38;5;255m', 'rich': 'white'}
        }
        
        # Initialize default box chars
        self._default_box_chars = {'─', '│', '╭', '╮', '╯', '╰'}
        
        # Set instance attributes with defaults or custom values
        self.formats = formats if formats is not None else self._default_formats.copy()
        self.colors = colors if colors is not None else self._default_colors.copy()
        self.box_chars = box_chars if box_chars is not None else self._default_box_chars.copy()
        self.patterns = patterns if patterns is not None else self._create_default_patterns()

    def _create_default_patterns(self) -> Dict[str, Pattern]:
        """Create the default set of text styling patterns."""
        base_patterns = {
            'quotes': {'start': '"', 'end': '"', 'color': 'PINK'},
            'brackets': {
                'start': '[', 
                'end': ']', 
                'color': 'GRAY', 
                'style': ['ITALIC'], 
                'remove_delimiters': True
            },
            'emphasis': {
                'start': '_', 
                'end': '_', 
                'color': None, 
                'style': ['ITALIC'], 
                'remove_delimiters': True
            },
            'strong': {
                'start': '*', 
                'end': '*', 
                'color': None, 
                'style': ['BOLD'], 
                'remove_delimiters': True
            }
        }
        
        # First pattern keeps delimiters and has no style
        base_patterns.update({
            k: {**v, 'style': [], 'remove_delimiters': False}
            for k, v in list(base_patterns.items())[:1]
        })
        
        patterns = {}
        used_delimiters = set()
        
        for name, cfg in base_patterns.items():
            pattern = Pattern(name=name, **cfg)
            
            # Validate unique delimiters
            if pattern.start in used_delimiters or pattern.end in used_delimiters:
                raise ValueError(f"Duplicate delimiter in pattern '{pattern.name}'")
            
            used_delimiters.update([pattern.start, pattern.end])
            patterns[name] = pattern
            
        return patterns

    def get_format(self, name: str) -> str:
        """Get a format code by name."""
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
            
        if any(p.start == pattern.start or p.end == pattern.end 
               for p in self.patterns.values()):
            raise ValueError(
                f"Pattern delimiters for '{pattern.name}' conflict with existing patterns"
            )
            
        self.patterns[pattern.name] = pattern