# display/style/__init__.py

from .definitions import StyleDefinitions
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

__all__ = ['DisplayStyle']
