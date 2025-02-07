from .dot_loader import AsyncDotLoader
from .reverse_streamer import ReverseStreamer

class Animations:
    def __init__(self, terminal, styles):
        self.terminal = terminal
        self.styles = styles

    def create_dot_loader(self, prompt, no_animation=False):
        loader = AsyncDotLoader(self.styles, prompt, no_animation)
        loader.terminal = self.terminal
        return loader

    def create_reverse_streamer(self, base_color='GREEN'):
        return ReverseStreamer(self.styles, self.terminal, base_color)