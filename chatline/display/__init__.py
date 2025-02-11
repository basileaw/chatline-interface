# display/__init__.py

from .io import DisplayIO
from .style import Displaystyle
from .terminal import DisplayTerminal
from .animations import DisplayAnimations

class Display:
    """Coordinates terminal display components."""
    def __init__(self):
        """Initialize components in dependency order."""
        self.terminal = DisplayTerminal()
        self.style = Displaystyle(terminal=self.terminal)
        self.io = DisplayIO(terminal=self.terminal, style=self.style)
        self.animations = DisplayAnimations(io=self.io, style=self.style)

__all__ = ['Display']
