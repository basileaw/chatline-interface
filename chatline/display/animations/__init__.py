# display/animations/__init__.py

from .dot_loader import AsyncDotLoader
from .reverse_streamer import ReverseStreamer

class DisplayAnimations:
    """
    Coordinates animation components for terminal display.
    
    Creates and initializes animation components (loaders and streamers) with the 
    provided display components.
    """
    def __init__(self, io, styles):
        """
        Initialize animation coordinator.
        
        Args:
            io: DisplayIO instance for output operations
            styles: DisplayStyles instance for text styling
        """
        self.io = io
        self.styles = styles

    def create_dot_loader(self, prompt, no_animation=False):
        """
        Create a loading animation with dots.
        
        Args:
            prompt: Text to display during loading
            no_animation: Whether to disable animation
        """
        loader = AsyncDotLoader(self.styles, prompt, no_animation)
        loader.utilities = self.io  # For backward compatibility with existing code
        return loader

    def create_reverse_streamer(self, base_color='GREEN'):
        """
        Create a reverse streaming animation effect.
        
        Args:
            base_color: Base color for the streamer
        """
        return ReverseStreamer(self.styles, self.io, base_color)