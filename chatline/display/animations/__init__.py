# display/animations/__init__.py

from .dot_loader import AsyncDotLoader
from .reverse_streamer import ReverseStreamer

class DisplayAnimations:
    """
    Coordinates animation components for terminal display.
    
    Creates and initializes animation components (loaders and streamers) with the 
    provided display utilities and styles components.
    """
    def __init__(self, utilities, styles):
        self.utilities = utilities
        self.styles = styles

    def create_dot_loader(self, prompt, no_animation=False):
        """Create a loading animation with dots."""
        loader = AsyncDotLoader(self.styles, prompt, no_animation)
        loader.utilities = self.utilities
        return loader

    def create_reverse_streamer(self, base_color='GREEN'):
        """Create a reverse streaming animation effect."""
        return ReverseStreamer(self.styles, self.utilities, base_color)

# Export components for direct access if needed
__all__ = ['DisplayAnimations', 'AsyncDotLoader', 'ReverseStreamer']