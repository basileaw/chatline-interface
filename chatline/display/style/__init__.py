# style/__init__.py

from .definition import DEFAULT_DEFINITIONS
from .strategies import DisplayStrategy, TextDisplayStrategy, PanelDisplayStrategy
from .engine import StyleEngine

class Displaystyle:
    """Wraps style definitions and application for terminal display."""
    def __init__(self, terminal=None):
        """Initialize with a terminal interface."""
        
        strategies = {
            "text": TextDisplayStrategy,
            "panel": PanelDisplayStrategy
        }
        
        self.application = StyleEngine(
            terminal=terminal,
            definitions=DEFAULT_DEFINITIONS,
            strategies=strategies
        )
        
    def __getattr__(self, name):
        """Delegate attribute access to the StyleEngine instance."""
        return getattr(self.application, name)