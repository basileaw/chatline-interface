# display/__init__.py

from .terminal import DisplayTerminal
from .style import DisplayStyle
from .animations import DisplayAnimations

class Display:
    """
    Coordinates terminal display components in a hierarchical structure.
    
    Component Hierarchy:
    DisplayTerminal (base) → StyleEngine → DisplayAnimations
    """
    def __init__(self):
        """Initialize components in dependency order."""
        self.terminal = DisplayTerminal()
        self.style = DisplayStyle(terminal=self.terminal)
        self.animations = DisplayAnimations(terminal=self.terminal, style=self.style)

__all__ = ['Display']