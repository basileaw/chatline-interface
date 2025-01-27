from typing import Optional, Protocol
from streaming_output.buffer import AsyncAdaptiveBuffer
from animations.dot_loader import AsyncDotLoader
from animations.reverse_stream import ReverseStreamer
from streaming_output.printer import OutputHandler
from state_managers.terminal_io import AsyncInterfaceManager
from state_managers.screen import AsyncScreenManager

# Local protocols to avoid circular imports
class Utilities(Protocol):
    def clear_screen(self) -> None: ...
    def get_visible_length(self, text: str) -> int: ...
    def write_and_flush(self, text: str) -> None: ...
    def hide_cursor(self) -> None: ...
    def show_cursor(self) -> None: ...
    def get_terminal_width(self) -> int: ...

class Painter(Protocol):
    def get_format(self, name: str) -> str: ...
    def get_color(self, name: str) -> str: ...
    @property
    def base_color(self) -> str: ...
    def process_chunk(self, text: str) -> str: ...
    def reset(self) -> None: ...

class StreamComponentFactory:
    """Factory for creating stream-related components."""
    
    def __init__(self, utilities: Utilities, painter: Painter):
        """
        Initialize factory with core dependencies.
        
        Args:
            utilities: Utilities instance for terminal operations
            painter: Painter instance for text styling
        """
        self.utils = utilities
        self.painter = painter
        self._interface_manager = None
        self._screen_manager = None

    @property
    def screen_manager(self) -> AsyncScreenManager:
        """Lazy initialization of screen manager."""
        if self._screen_manager is None:
            self._screen_manager = AsyncScreenManager(
                utilities=self.utils,
                painter=self.painter
            )
        return self._screen_manager

    @property
    def interface_manager(self) -> AsyncInterfaceManager:
        """Lazy initialization of interface manager."""
        if self._interface_manager is None:
            self._interface_manager = AsyncInterfaceManager(
                utilities=self.utils,
                painter=self.painter
            )
        return self._interface_manager

    def create_adaptive_buffer(self) -> AsyncAdaptiveBuffer:
        """Create a new AsyncAdaptiveBuffer instance."""
        return AsyncAdaptiveBuffer()

    def create_dot_loader(self,
                         prompt: str,
                         output_handler: Optional[OutputHandler] = None,
                         no_animation: bool = False) -> AsyncDotLoader:
        """
        Create a new AsyncDotLoader instance.
        
        Args:
            prompt: The prompt text to display
            output_handler: Optional output handler for processing text
            no_animation: Whether to disable animation
            
        Returns:
            AsyncDotLoader: Configured dot loader instance
        """
        adaptive_buffer = self.create_adaptive_buffer()
        return AsyncDotLoader(
            utilities=self.utils,
            prompt=prompt,
            adaptive_buffer=adaptive_buffer,
            output_handler=output_handler,
            no_animation=no_animation
        )

    def create_reverse_streamer(self) -> ReverseStreamer:
        """Create a new ReverseStreamer instance."""
        return ReverseStreamer(
            utilities=self.utils,
            painter=self.painter
        )

    def create_output_handler(self) -> OutputHandler:
        """Create a new OutputHandler instance."""
        return OutputHandler(
            painter=self.painter,
            utilities=self.utils
        )