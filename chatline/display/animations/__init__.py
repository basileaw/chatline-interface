# display/animations/__init__.py

from .dot_loader import AsyncDotLoader
from .reverse_streamer import ReverseStreamer
from .scroller import Scroller

class DisplayAnimations:
    """
    Animation layer that builds on terminal and style capabilities.
    
    Component Hierarchy:
    DisplayTerminal → StyleEngine → DisplayAnimations
    """
    def __init__(self, terminal, style):
        """Initialize with terminal and style dependencies."""
        self.terminal = terminal
        self.style = style

    def create_dot_loader(self, prompt, no_animation=False):
        """Create and return a dot loader animation."""
        loader = AsyncDotLoader(self.style, self.terminal, prompt, no_animation)
        return loader

    def create_reverse_streamer(self, base_color='GREEN'):
        """Create and return a reverse streaming animation effect."""
        return ReverseStreamer(self.style, self.terminal, base_color)
    
    def create_scroller(self):
        """Create and return a text scrolling animation handler."""
        return Scroller(self.style, self.terminal)