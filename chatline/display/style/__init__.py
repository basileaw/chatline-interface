# style/__init__.py

from .definitions import StyleDefinitions
from .strategies import StyleStrategies
from .engine import StyleEngine

class Displaystyle:
    """Wraps style definitions and application for terminal display."""
    def __init__(self, terminal=None):
        """Initialize with a terminal interface."""
        self.application = StyleEngine(
            terminal=terminal,
            definitions=StyleDefinitions(),
            strategies=StyleStrategies()
        )
        
    def __getattr__(self, name):
        """Delegate attribute access to the StyleEngine instance."""
        return getattr(self.application, name)