# display/animations/__init__.py

from .dot_loader import AsyncDotLoader
from .reverse_streamer import ReverseStreamer
from .scroller import Scroller

class DisplayAnimations:
    """Coordinates terminal animation components."""
    def __init__(self, io, styles):
        """Initialize with DisplayIO and DisplayStyles instances."""
        self.io = io
        self.styles = styles

    def create_dot_loader(self, prompt, no_animation=False):
        """Create and return a dot loader animation."""
        loader = AsyncDotLoader(self.styles, prompt, no_animation)
        loader.utilities = self.io  # Backward compatibility
        return loader

    def create_reverse_streamer(self, base_color='GREEN'):
        """Create and return a reverse streaming animation effect."""
        return ReverseStreamer(self.styles, self.io, base_color)
    
    def create_scroller(self):
        """Create and return a text scrolling animation handler."""
        return Scroller(self.styles, self.io)