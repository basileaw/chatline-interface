# display/style/definitions.py

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Union, Tuple

@dataclass
class Pattern:
    """Config for a text styling pattern."""
    name: str
    start: Union[str, List[str]]  # Can be a single char or list of chars
    end: Union[str, List[str]]    # Can be a single char or list of chars
    color: Optional[str] = None
    style: Optional[List[str]] = None
    remove_delimiters: bool = False
    
    def get_start_chars(self) -> List[str]:
        """Return start delimiters as a list."""
        if isinstance(self.start, list):
            return self.start
        return [self.start]
        
    def get_end_chars(self) -> List[str]:
        """Return end delimiters as a list."""
        if isinstance(self.end, list):
            return self.end
        return [self.end]

class StyleDefinitions:
    """Container for style definitions."""
    
    FMT = staticmethod(lambda x: f'\033[{x}m')  # ANSI format utility
    
    def __init__(
        self,
        formats: Optional[Dict[str, str]] = None,
        colors: Optional[Dict[str, Dict[str, str]]] = None,
        box_chars: Optional[Set[str]] = None,
        patterns: Optional[Dict[str, Pattern]] = None
    ):
        """Initialize definitions with optional custom configs."""
        # Default ANSI formats
        self._default_formats = {
            'RESET': self.FMT('0'),
            'ITALIC_ON': self.FMT('3'),
            'ITALIC_OFF': self.FMT('23'),
            'BOLD_ON': self.FMT('1'),
            'BOLD_OFF': self.FMT('22')
        }
        # Default colors
        self._default_colors = {
            'GREEN': {'ansi': '\033[38;5;47m', 'rich': 'green3'},
            'PINK': {'ansi': '\033[38;5;212m', 'rich': 'pink1'},
            'BLUE': {'ansi': '\033[38;5;75m', 'rich': 'blue1'},
            'GRAY': {'ansi': '\033[38;5;245m', 'rich': 'gray50'},
            'YELLOW': {'ansi': '\033[38;5;227m', 'rich': 'yellow1'},
            'WHITE': {'ansi': '\033[38;5;255m', 'rich': 'white'},
            'PURPLE': {'ansi': '\033[38;5;129m', 'rich': 'purple3'}
        }
        # Default box-drawing characters
        self._default_box_chars = {'─', '│', '╭', '╮', '╯', '╰'}
        
        # Initialize delimiter map (will be populated after patterns are created)
        self._delimiter_to_pattern_map = {}
        
        self.formats = formats if formats is not None else self._default_formats.copy()
        self.colors = colors if colors is not None else self._default_colors.copy()
        self.box_chars = box_chars if box_chars is not None else self._default_box_chars.copy()
        self.patterns = patterns if patterns is not None else self._create_default_patterns()
        
        # Now create the delimiter map
        self._delimiter_to_pattern_map = self._create_delimiter_map()

    def _create_delimiter_map(self) -> Dict[str, List[Tuple[str, bool]]]:
        """
        Create a mapping from each delimiter character to its pattern uses.
        This allows for quick lookup of patterns by delimiter character.
        
        Returns:
            Dict mapping delimiter char to list of tuples (pattern_name, is_start)
            where is_start indicates if it's a start delimiter (True) or end delimiter (False)
        """
        delimiter_map = {}
        for name, pattern in self.patterns.items():
            # Map start delimiters
            for start_char in pattern.get_start_chars():
                delimiter_map.setdefault(start_char, []).append((name, True))
            # Map end delimiters
            for end_char in pattern.get_end_chars():
                delimiter_map.setdefault(end_char, []).append((name, False))
        return delimiter_map

    def _create_default_patterns(self) -> Dict[str, Pattern]:
        """Create default styling patterns with Unicode support."""
        base_patterns = {
            'quotes': {
                'start': ['"', '\u201c'],  # ASCII quote and LEFT DOUBLE QUOTATION MARK
                'end': ['"', '\u201d'],    # ASCII quote and RIGHT DOUBLE QUOTATION MARK
                'color': 'PINK'
            },
            'brackets': {
                'start': ['['],
                'end': [']'],
                'color': 'GRAY', 
                'style': ['ITALIC'], 
                'remove_delimiters': True
            },
            'emphasis': {
                'start': ['_', '*'],  # Support both underscore and asterisk for italic
                'end': ['_', '*'],
                'color': None, 
                'style': ['ITALIC'], 
                'remove_delimiters': True
            },
            'strong': {
                'start': ['**', '__'],  # Support double characters for bold
                'end': ['**', '__'],
                'color': None, 
                'style': ['BOLD'], 
                'remove_delimiters': True
            },
            'highlight': {
                'start': ['~+'],
                'end': ['+~'],
                'color': 'PURPLE',
                'style': ['BOLD', 'ITALIC'],
                'remove_delimiters': True
            }
        }
        # First pattern: keep delimiters and no style
        base_patterns.update({
            k: {**v, 'style': [], 'remove_delimiters': False}
            for k, v in list(base_patterns.items())[:1]
        })
        
        patterns = {}
        used_delimiters = set()
        pattern_delimiters = {}  # Track which delimiters belong to which pattern
        
        for name, cfg in base_patterns.items():
            pattern = Pattern(name=name, **cfg)
            
            # Special case for patterns where same character can be both start and end
            # (like quotes, emphasis, and strong)
            if name in ['quotes', 'emphasis', 'strong']:
                # For these patterns, we know the same character is used for both start and end
                # Track start and end delimiters separately to allow the same character in both
                start_chars = set(pattern.get_start_chars())
                end_chars = set(pattern.get_end_chars())
                
                # Check for conflicts with other patterns' delimiters
                for delim in start_chars:
                    if delim in used_delimiters:
                        conflict_pattern = next((p for p, chars in pattern_delimiters.items() 
                                              if p != name and delim in chars), None)
                        if conflict_pattern:  # Only error if it's from a different pattern
                            raise ValueError(f"Duplicate delimiter '{delim}' in pattern '{name}', "
                                           f"already used in '{conflict_pattern}'")
                
                for delim in end_chars:
                    if delim in used_delimiters:
                        conflict_pattern = next((p for p, chars in pattern_delimiters.items() 
                                              if p != name and delim in chars), None)
                        if conflict_pattern:  # Only error if it's from a different pattern
                            raise ValueError(f"Duplicate delimiter '{delim}' in pattern '{name}', "
                                           f"already used in '{conflict_pattern}'")
                
                # Add all delimiters to tracking sets
                used_delimiters.update(start_chars)
                used_delimiters.update(end_chars)
                pattern_delimiters[name] = start_chars.union(end_chars)
            else:
                # Regular case - check start and end delimiters separately
                for start_char in pattern.get_start_chars():
                    if start_char in used_delimiters:
                        conflict_pattern = next((p for p, chars in pattern_delimiters.items() 
                                              if start_char in chars), None)
                        raise ValueError(f"Duplicate delimiter '{start_char}' in pattern '{name}', "
                                       f"already used in '{conflict_pattern}'")
                    used_delimiters.add(start_char)
                    pattern_delimiters.setdefault(name, set()).add(start_char)
                    
                for end_char in pattern.get_end_chars():
                    if end_char in used_delimiters:
                        conflict_pattern = next((p for p, chars in pattern_delimiters.items() 
                                              if end_char in chars), None)
                        raise ValueError(f"Duplicate delimiter '{end_char}' in pattern '{name}', "
                                       f"already used in '{conflict_pattern}'")
                    used_delimiters.add(end_char)
                    pattern_delimiters.setdefault(name, set()).add(end_char)
            
            patterns[name] = pattern
            
        return patterns

    def get_format(self, name: str) -> str:
        """Return format code for the given name."""
        return self.formats.get(name, '')

    def get_color(self, name: str) -> Dict[str, str]:
        """Return color config for the given name."""
        return self.colors.get(name, {'ansi': '', 'rich': ''})

    def get_pattern(self, name: str) -> Optional[Pattern]:
        """Return pattern for the given name."""
        return self.patterns.get(name)
        
    def get_pattern_by_delimiter(self, char: str) -> List[Tuple[Optional[Pattern], bool]]:
        """
        Get all patterns that use this delimiter character.
        
        Args:
            char: The delimiter character to look up
            
        Returns:
            List of tuples (pattern, is_start_delimiter) for all patterns
            that use this character as a delimiter
        """
        if char not in self._delimiter_to_pattern_map:
            return []
            
        result = []
        for pattern_name, is_start in self._delimiter_to_pattern_map[char]:
            pattern = self.patterns.get(pattern_name)
            if pattern:
                result.append((pattern, is_start))
        return result

    def add_pattern(self, pattern: Pattern) -> None:
        """Add a new pattern; raise error on delimiter/name conflict."""
        if pattern.name in self.patterns:
            raise ValueError(f"Pattern '{pattern.name}' already exists")
            
        # Check for delimiter conflicts
        for start_char in pattern.get_start_chars():
            if start_char in self._delimiter_to_pattern_map:
                raise ValueError(f"Pattern delimiter '{start_char}' conflicts with existing patterns")
                
        for end_char in pattern.get_end_chars():
            if end_char in self._delimiter_to_pattern_map:
                raise ValueError(f"Pattern delimiter '{end_char}' conflicts with existing patterns")
                
        # Add the pattern
        self.patterns[pattern.name] = pattern
        
        # Update the delimiter map
        for start_char in pattern.get_start_chars():
            self._delimiter_to_pattern_map[start_char] = (pattern.name, True)
        for end_char in pattern.get_end_chars():
            self._delimiter_to_pattern_map[end_char] = (pattern.name, False)
