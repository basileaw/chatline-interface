# factories.py

from typing import Optional, Any
from adaptive_buffer import AdaptiveBuffer
from dot_loader import DotLoader
from reverse_stream import ReverseStreamer
from output_handler import OutputHandler
import os

class StreamComponentFactory:
    """Factory for creating stream-related components."""
    
    def __init__(self, text_painter):
        """
        Initialize the factory.
        
        Args:
            text_painter: TextPainter instance for styling
        """
        self.text_painter = text_painter
        self._use_async = os.environ.get('USE_ASYNC_LOADER', '').lower() == 'true'

    def create_adaptive_buffer(self) -> AdaptiveBuffer:
        """Create a new AdaptiveBuffer instance."""
        return AdaptiveBuffer()

    def create_dot_loader(self, 
                         prompt: str, 
                         output_handler: Optional[OutputHandler] = None,
                         no_animation: bool = False) -> Any:
        """
        Create a dot loader instance.
        
        Args:
            prompt: The prompt text to display
            output_handler: Handler for text output
            no_animation: Whether to disable animation
            
        Returns:
            Either DotLoader or AsyncDotLoader based on environment variable
        """
        adaptive_buffer = self.create_adaptive_buffer()
        
        if self._use_async:
            # Only import AsyncDotLoader if we're using it
            from async_dot_loader import AsyncDotLoader
            return AsyncDotLoader(
                prompt=prompt,
                adaptive_buffer=adaptive_buffer,
                output_handler=output_handler,
                no_animation=no_animation
            )
        else:
            return DotLoader(
                prompt=prompt,
                adaptive_buffer=adaptive_buffer,
                output_handler=output_handler,
                no_animation=no_animation
            )

    def create_reverse_streamer(self) -> ReverseStreamer:
        """Create a new ReverseStreamer instance."""
        return ReverseStreamer(self.text_painter)