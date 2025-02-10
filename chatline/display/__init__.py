# display/__init__.py

from .io import DisplayIO
from .styles import DisplayStyles
from .terminal import DisplayTerminal
from .animations import DisplayAnimations

class Display:
    """Coordinates terminal display components."""
    def __init__(self):
        """Initialize components in dependency order."""
        self.terminal = DisplayTerminal()
        self.styles = DisplayStyles(terminal=self.terminal)
        self.io = DisplayIO(terminal=self.terminal, styles=self.styles)
        self.animations = DisplayAnimations(io=self.io, styles=self.styles)

__all__ = ['Display']
