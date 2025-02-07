# interface.py

import os
from typing import Optional, Dict, Any, Callable
from .terminal import Terminal
from .conversation import Conversation, StateManager
from .animations import Animations
from .styles import Styles
from .stream import EmbeddedStream, RemoteStream
from .generator import generate_stream
from .logger import setup_logger

class Interface:
    def __init__(self, endpoint: Optional[str] = None, generator_func: Optional[Callable] = None):
        self.logger = setup_logger(__name__)
        self._init_components(endpoint or None, generator_func or generate_stream)

    def _init_components(self, endpoint: Optional[str], generator_func: Callable) -> None:
        try:
            # Initialize UI components
            self.terminal = Terminal(styles=None)
            self.styles = Styles(terminal=self.terminal)
            self.terminal.styles = self.styles
            self.animations = Animations(terminal=self.terminal, styles=self.styles)
            
            # Initialize state and stream with logger injection
            self.state_manager = StateManager(logger=self.logger)
            self.stream = (RemoteStream(endpoint, logger=self.logger)
                           if endpoint 
                           else EmbeddedStream(generator_func, logger=self.logger))
            
            # Initialize conversation with the wrapped generator
            self.conversation = Conversation(
                terminal=self.terminal,
                generator_func=self._wrap_generator(self.stream.get_generator()),
                styles=self.styles,
                animations_manager=self.animations
            )
            
            # Setup terminal (clear and hide cursor)
            self.terminal._clear_screen()
            self.terminal._hide_cursor()
            
        except Exception as e:
            self.logger.error(f"Init error: {str(e)}")
            raise

    def _wrap_generator(self, generator_func: Callable) -> Callable:
        async def wrapped_generator(messages: list, **kwargs: Any):
            try:
                current_state = self.state_manager.get_current_state()
                async for chunk in generator_func(
                    messages, 
                    state=current_state.to_dict() if current_state else None,
                    **kwargs
                ):
                    yield chunk
            except Exception as e:
                self.logger.error(f"Generator error: {str(e)}")
                yield f"Error during generation: {str(e)}"
        return wrapped_generator

    def preface(self, text: str, color: Optional[str] = None, display_type: str = "panel") -> None:
        try:
            self.conversation.preface(text, color, display_type)
            self.logger.debug(f"Added preface: {text[:50]}")
        except Exception as e:
            self.logger.error(f"Preface error: {str(e)}")
            raise

    def start(self, messages: Optional[Dict[str, str]] = None) -> None:
        try:
            self.conversation.start(messages)
        except KeyboardInterrupt:
            self.logger.info("User interrupted")
        except Exception as e:
            self.logger.error(f"Start error: {str(e)}")
            raise
        finally:
            self.terminal._show_cursor()
            self.terminal._clear_screen()
            self.state_manager.clear_history()
