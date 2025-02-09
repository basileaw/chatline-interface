# display/styles/__init__.py

from .definition import DEFAULT_DEFINITIONS, StyleDefinitions
from .application import StyleApplication

class DisplayStyles:
    """
    Coordinates style definitions and application for terminal display.
    
    This class acts as a thin wrapper around the style application system,
    providing access to styling functionality while maintaining separation
    between style definitions and their application logic.
    """
    def __init__(self, terminal=None):
        """
        Initialize the display styles coordinator.
        
        Args:
            terminal: Terminal interface for display operations
        """
        self.application = StyleApplication(
            terminal=terminal,
            definitions=DEFAULT_DEFINITIONS
        )
        
    def __getattr__(self, name):
        """
        Delegate all undefined attribute access to the style application.
        
        This allows the DisplayStyles class to maintain backward compatibility
        by exposing all StyleApplication methods without explicitly defining them.
        
        Args:
            name: Name of the requested attribute
            
        Returns:
            The requested attribute from the StyleApplication instance
            
        Raises:
            AttributeError: If the attribute doesn't exist in StyleApplication
        """
        return getattr(self.application, name)