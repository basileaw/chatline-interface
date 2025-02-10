# display/__init__.py

from .terminal import DisplayTerminal
from .styles import DisplayStyles
from .io import DisplayIO
from .animations import DisplayAnimations

class Display:
    """
    Coordinates display components for terminal-based interfaces.
    
    This class acts as a coordinator between DisplayTerminal, DisplayStyles,
    DisplayIO, and DisplayAnimations, managing their initialization order
    and dependencies while providing a clean public interface.
    """
    def __init__(self):
        """Initialize display system."""
        # Initialize terminal first as other components depend on it
        self.terminal = DisplayTerminal()
        
        # Initialize styles with terminal for dimension-aware formatting
        self.styles = DisplayStyles(terminal=self.terminal)
        
        # Initialize I/O with terminal and styles dependencies
        self.io = DisplayIO(
            terminal=self.terminal,
            styles=self.styles
        )
        
        # Initialize animations with all required dependencies
        self.animations = DisplayAnimations(
            io=self.io,
            styles=self.styles
        )

# Export components for direct access
__all__ = ['Display', 'DisplayTerminal', 'DisplayStyles', 'DisplayIO', 'DisplayAnimations']