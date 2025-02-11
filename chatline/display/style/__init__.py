# display/style/__init__.py

from .definitions import StyleDefinitions
from .strategies import StyleStrategies
from .engine import StyleEngine as BaseStyleEngine

class DisplayStyle:
    """
    Primary style coordination layer that wraps around terminal operations.
    
    This class serves as the main interface for all styling operations,
    building upon the terminal layer to provide text styling capabilities.
    
    Component Hierarchy:
    DisplayStyle → BaseStyleEngine → StyleStrategies → StyleDefinitions → Terminal
    """
    def __init__(self, terminal):
        """
        Initialize the style system with terminal dependency.
        
        Args:
            terminal: DisplayTerminal instance for base terminal operations
        """
        # Initialize in dependency order
        self.definitions = StyleDefinitions()
        self.strategies = StyleStrategies(self.definitions, terminal)
        self._engine = BaseStyleEngine(
            terminal=terminal,
            definitions=self.definitions,
            strategies=self.strategies
        )
        
    def __getattr__(self, name):
        """Delegate unknown attribute access to the style engine instance."""
        return getattr(self._engine, name)

# Export the main interface
__all__ = ['DisplayStyle']