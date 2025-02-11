# style/__init__.py

from .definitions import DEFAULT_DEFINITIONS
from .strategies import StyleStrategy
from .engine import StyleEngine

class Displaystyle:
    """Wraps style definitions and application for terminal display."""
    def __init__(self, terminal=None):
        """Initialize with a terminal interface."""
        self.application = StyleEngine(
            terminal=terminal,
            definitions=DEFAULT_DEFINITIONS,
            strategy=StyleStrategy()
        )
        
    def __getattr__(self, name):
        """Delegate attribute access to the StyleEngine instance."""
        return getattr(self.application, name)