from typing import Optional, Protocol
from stream.printer import OutputHandler
from stream.buffer import AsyncAdaptiveBuffer
from animations.dot_loader import AsyncDotLoader
from animations.reverse_stream import ReverseStreamer
from state.terminal import TerminalManager
from state.conversation import ConversationManager

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
    def __init__(self, utilities: Utilities, painter: Painter):
        self.utils = utilities
        self.painter = painter
        self._terminal = None
        self._conversation = None
        self._generator_func = None

    @property
    def terminal(self) -> TerminalManager:
        if not self._terminal:
            self._terminal = TerminalManager(self.utils, self.painter)
        return self._terminal

    @property
    def conversation(self) -> ConversationManager:
        if not self._conversation:
            if not self._generator_func:
                raise ValueError("Generator function must be set before accessing conversation manager")
            self._conversation = ConversationManager(
                self.terminal, self._generator_func, self
            )
        return self._conversation

    def set_generator(self, generator_func):
        self._generator_func = generator_func
        self._conversation = None

    def create_output_handler(self) -> OutputHandler:
        return OutputHandler(self.painter, self.utils)

    def create_adaptive_buffer(self) -> AsyncAdaptiveBuffer:
        return AsyncAdaptiveBuffer()

    def create_dot_loader(self, prompt: str, output_handler: Optional[OutputHandler] = None,
                         no_animation: bool = False) -> AsyncDotLoader:
        return AsyncDotLoader(
            utilities=self.utils,
            prompt=prompt,
            adaptive_buffer=self.create_adaptive_buffer(),
            output_handler=output_handler,
            no_animation=no_animation
        )

    def create_reverse_streamer(self) -> ReverseStreamer:
        return ReverseStreamer(self.utils, self.painter)

    # Compatibility properties
    screen_manager = interface_manager = property(lambda self: self.terminal)