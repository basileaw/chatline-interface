# display/styles/definition.py

from dataclasses import dataclass
from typing import Dict, List, Optional

# Core formatting utilities
FMT = lambda x: f'\033[{x}m'

# Format definitions
FORMATS = {
    'RESET': FMT('0'),
    'ITALIC_ON': FMT('3'),
    'ITALIC_OFF': FMT('23'),
    'BOLD_ON': FMT('1'),
    'BOLD_OFF': FMT('22')
}

# Color definitions with both ANSI and Rich color mappings
COLORS = {
    'GREEN': {'ansi': '\033[38;5;47m', 'rich': 'green3'},
    'PINK':  {'ansi': '\033[38;5;212m', 'rich': 'pink1'},
    'BLUE':  {'ansi': '\033[38;5;75m', 'rich': 'blue1'},
    'GRAY':  {'ansi': '\033[38;5;245m', 'rich': 'gray50'},
    'YELLOW': {'ansi': '\033[38;5;227m', 'rich': 'yellow1'},
    'WHITE': {'ansi': '\033[38;5;255m', 'rich': 'white'}
}

# Box drawing characters
BOX_CHARS = {'─', '│', '╭', '╮', '╯', '╰'}

@dataclass
class Pattern:
    """
    Defines a text pattern for styling.
    
    Attributes:
        name: Unique identifier for the pattern
        start: Opening delimiter
        end: Closing delimiter
        color: Optional color name from COLORS
        styles: Optional list of style names from FORMATS
        remove_delimiters: Whether to strip delimiters when applying the pattern
    """
    name: str
    start: str
    end: str
    color: Optional[str] = None
    styles: Optional[List[str]] = None
    remove_delimiters: bool = False

@dataclass
class StyleDefinitions:
    """
    Bundles all style-related definitions.
    
    This class serves as a container for all style-related configurations,
    ensuring they stay together while allowing for potential future
    customization through dependency injection.
    
    Attributes:
        formats: Format code definitions
        colors: Color definitions with ANSI and Rich mappings
        box_chars: Box-drawing characters for borders
        patterns: Pattern definitions for text styling
    """
    formats: Dict[str, str]
    colors: Dict[str, Dict[str, str]]
    box_chars: set
    patterns: Dict[str, Pattern]
    
    @classmethod
    def create_default_patterns(cls) -> Dict[str, Pattern]:
        """
        Create the default set of text styling patterns.
        
        Returns:
            Dictionary mapping pattern names to Pattern instances
        """
        base_patterns = {
            'quotes': {'start': '"', 'end': '"', 'color': 'PINK'},
            'brackets': {'start': '[', 'end': ']', 'color': 'GRAY', 'styles': ['ITALIC'], 'remove_delimiters': True},
            'emphasis': {'start': '_', 'end': '_', 'color': None, 'styles': ['ITALIC'], 'remove_delimiters': True},
            'strong': {'start': '*', 'end': '*', 'color': None, 'styles': ['BOLD'], 'remove_delimiters': True}
        }
        
        # Update first pattern to have no styles and keep delimiters
        base_patterns.update({k: {**v, 'styles': [], 'remove_delimiters': False} 
                            for k, v in list(base_patterns.items())[:1]})
        
        patterns = {}
        used_delimiters = set()
        
        # Convert pattern configs to Pattern instances
        for name, cfg in base_patterns.items():
            pattern = Pattern(name=name, **cfg)
            
            # Ensure no delimiter conflicts
            if pattern.start in used_delimiters or pattern.end in used_delimiters:
                raise ValueError(f"Duplicate delimiter in pattern '{pattern.name}'")
            
            used_delimiters.update([pattern.start, pattern.end])
            patterns[name] = pattern
            
        return patterns

# Create the default style definitions instance
DEFAULT_DEFINITIONS = StyleDefinitions(
    formats=FORMATS,
    colors=COLORS,
    box_chars=BOX_CHARS,
    patterns=StyleDefinitions.create_default_patterns()
)