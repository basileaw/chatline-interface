# factories.py

from typing import Optional
from streaming_output.buffer import AsyncAdaptiveBuffer
from animations.dot_loader import AsyncDotLoader
from animations.reverse_stream import ReverseStreamer
from streaming_output.printer import OutputHandler
from state_managers.terminal_io import AsyncInterfaceManager
from state_managers.screen import AsyncScreenManager

class StreamComponentFactory:
    """Factory for creating stream-related components."""
    
    def __init__(self, text_painter):
        self.text_painter = text_painter
        self._interface_manager = None
        self._screen_manager = None
        
    @property
    def screen_manager(self) -> AsyncScreenManager:
        """Lazy initialization of screen manager."""
        if self._screen_manager is None:
            self._screen_manager = AsyncScreenManager()
        return self._screen_manager
        
    @property
    def interface_manager(self) -> AsyncInterfaceManager:
        """Lazy initialization of interface manager."""
        if self._interface_manager is None:
            self._interface_manager = AsyncInterfaceManager()
        return self._interface_manager

    def create_adaptive_buffer(self) -> AsyncAdaptiveBuffer:
        """Create a new AsyncAdaptiveBuffer instance."""
        return AsyncAdaptiveBuffer()

    def create_dot_loader(self, 
                         prompt: str, 
                         output_handler: Optional[OutputHandler] = None,
                         no_animation: bool = False) -> AsyncDotLoader:
        """Create a new AsyncDotLoader instance."""
        adaptive_buffer = self.create_adaptive_buffer()
        return AsyncDotLoader(
            prompt=prompt,
            adaptive_buffer=adaptive_buffer,
            output_handler=output_handler,
            no_animation=no_animation
        )

    def create_reverse_streamer(self) -> ReverseStreamer:
        """Create a new ReverseStreamer instance."""
        return ReverseStreamer(self.text_painter)