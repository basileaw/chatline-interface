# display/__init__.py

from .utilities import DisplayUtilities 
from .styles import DisplayStyles

class Display:
    """
    Coordinates display components for terminal-based interfaces.
    
    This class acts as a thin coordinator between DisplayUtilities and DisplayStyles,
    allowing direct access to both components while managing their interdependencies.
    """
    def __init__(self):
        # Initialize components with None references first to avoid circular dependency
        self.utilities = DisplayUtilities(styles=None)
        self.styles = DisplayStyles(utilities=self.utilities)
        
        # Connect the components after initialization
        self.utilities.styles = self.styles

    def reset(self):
        """Reset the display state by showing cursor and clearing screen."""
        self.utilities.reset()

# Export components for direct access
__all__ = ['Display', 'DisplayUtilities', 'DisplayStyles']