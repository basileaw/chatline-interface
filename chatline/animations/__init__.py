# animations/__init__.py

from .dot_loader import AsyncDotLoader
from .reverse_streamer import ReverseStreamer

class Animations:
    """
    Coordinates animation components for terminal display.
    
    Creates and initializes animation components with display utilities and styles.
    """
    def __init__(self, utilities, styles):
        self.utilities = utilities
        self.styles = styles

    def create_dot_loader(self, prompt, no_animation=False):
        loader = AsyncDotLoader(self.styles, prompt, no_animation)
        loader.utilities = self.utilities
        return loader

    def create_reverse_streamer(self, base_color='GREEN'):
        return ReverseStreamer(self.styles, self.utilities, base_color)