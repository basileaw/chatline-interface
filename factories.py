from typing import Optional, Protocol
from stream.printer import OutputHandler
from stream.buffer import AsyncAdaptiveBuffer
from animations.dot_loader import AsyncDotLoader
from animations.reverse_stream import ReverseStreamer
from state.terminal import TerminalManager  # Updated path
from state.conversation import ConversationManager  # Updated path

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
        self.utils = utilities
        self.painter = painter
        self._terminal = None
        self._conversation = None
        self._generator_func = None

    @property
    def terminal(self) -> TerminalManager:
        """Lazy initialization of terminal manager."""
        if self._terminal is None:
            self._terminal = TerminalManager(
                utilities=self.utils,
                painter=self.painter
            )
        return self._terminal

    @property
    def conversation(self) -> ConversationManager:
        """Lazy initialization of conversation manager."""
        if self._conversation is None:
            if not self._generator_func:
                raise ValueError("Generator function must be set before accessing conversation manager")
            self._conversation = ConversationManager(
                terminal=self.terminal,
                generator_func=self._generator_func,
                component_factory=self
            )
        return self._conversation

    def set_generator(self, generator_func):
        """Set the generator function for the conversation manager."""
        self._generator_func = generator_func
        # Reset conversation manager if it exists
        self._conversation = None

    def create_output_handler(self) -> OutputHandler:
        """Create a new OutputHandler instance."""
        return OutputHandler(
            painter=self.painter,
            utilities=self.utils
        )

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

    # Compatibility methods - terminal now handles both screen and interface operations
    @property
    def screen_manager(self):
        return self.terminal

    @property
    def interface_manager(self):
        return self.terminal