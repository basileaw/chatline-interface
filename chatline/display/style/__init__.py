# display/style/__init__.py

from .definitions import StyleDefinitions, Pattern
from .strategies import StyleStrategies
from .engine import StyleEngine as BaseStyleEngine

class DisplayStyle:
    """Main interface wrapping styling operations and terminal handling."""
    def __init__(self, terminal):
        """Initialize style system with terminal dependency."""
        self.definitions = StyleDefinitions()  # Create default style definitions
        self.strategies = StyleStrategies(self.definitions, terminal)  # Init formatting strategies
        self._engine = BaseStyleEngine(terminal=terminal, definitions=self.definitions, strategies=self.strategies)

    def __getattr__(self, name):
        """Delegate attribute access to the underlying style engine."""
        return getattr(self._engine, name)
    
    def add_unicode_pattern(self, name: str, start_chars: list, end_chars: list, 
                           color: str = None, style: list = None, 
                           remove_delimiters: bool = False) -> None:
        """
        Add a new styling pattern with Unicode support.
        
        Args:
            name: Pattern name
            start_chars: List of start delimiter characters
            end_chars: List of end delimiter characters
            color: Color name to apply (default: None)
            style: List of styles to apply (default: None)
            remove_delimiters: Whether to remove delimiters (default: False)
        """
        pattern = Pattern(
            name=name, 
            start=start_chars, 
            end=end_chars,
            color=color,
            style=style,
            remove_delimiters=remove_delimiters
        )
        self.definitions.add_pattern(pattern)

__all__ = ['DisplayStyle', 'Pattern']