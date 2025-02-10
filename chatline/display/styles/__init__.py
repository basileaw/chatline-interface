# styles/__init__.py

from .definition import DEFAULT_DEFINITIONS
from .application import StyleApplication

class DisplayStyles:
    """Wraps style definitions and application for terminal display."""
    def __init__(self, terminal=None):
        """Initialize with a terminal interface."""
        self.application = StyleApplication(
            terminal=terminal,
            definitions=DEFAULT_DEFINITIONS
        )
        
    def __getattr__(self, name):
        """Delegate attribute access to the StyleApplication instance."""
        return getattr(self.application, name)
