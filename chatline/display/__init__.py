# display/__init__.py

from .utilities import DisplayUtilities 
from .styles import DisplayStyles
from .animations import DisplayAnimations

class Display:
    """
    Coordinates display components for terminal-based interfaces.
    
    This class acts as a coordinator between DisplayUtilities, DisplayStyles, and
    DisplayAnimations, allowing direct access to all components while managing their
    interdependencies.
    """
    def __init__(self):
        # Initialize components with None references first to avoid circular dependency
        self.utilities = DisplayUtilities(styles=None)
        self.styles = DisplayStyles(utilities=self.utilities)
        
        # Connect the core components
        self.utilities.styles = self.styles
        
        # Initialize animations with the connected components
        self.animations = DisplayAnimations(
            utilities=self.utilities,
            styles=self.styles
        )

    def reset(self):
        """Reset the display state by showing cursor and clearing screen."""
        self.utilities.reset()

# Export components for direct access
__all__ = ['Display', 'DisplayUtilities', 'DisplayStyles', 'DisplayAnimations']