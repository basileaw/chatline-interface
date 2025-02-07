# interface.py

import os
import logging
from typing import Optional, Dict, Any, Callable
from .display import Display
from .conversation import Conversation, StateManager
from .animations import Animations
from .stream import EmbeddedStream, RemoteStream
from .generator import generate_stream
from .logger import get_logger

class Interface:
    """
    Main interface coordinator for the chat application.
    
    Initializes and connects all components including display, conversation,
    animations, and stream handling.
    """
    def __init__(
        self, 
        endpoint: Optional[str] = None, 
        generator_func: Optional[Callable] = None, 
        logging_enabled: bool = False
    ):
        # Get a logger that either logs to file or uses a NullHandler
        self.logger = get_logger(__name__, logging_enabled)
        self._init_components(endpoint or None, generator_func or generate_stream)

    def _init_components(self, endpoint: Optional[str], generator_func: Callable) -> None:
        try:
            # Initialize display coordinator
            self.display = Display()
            
            # Initialize animations with display components
            self.animations = Animations(
                utilities=self.display.utilities,
                styles=self.display.styles
            )
            
            # Initialize state and stream with logger injection
            self.state_manager = StateManager(logger=self.logger)
            self.stream = (RemoteStream(endpoint, logger=self.logger)
                         if endpoint 
                         else EmbeddedStream(generator_func, logger=self.logger))
            
            # Initialize conversation with display components
            self.conversation = Conversation(
                utilities=self.display.utilities,
                styles=self.display.styles,
                generator_func=self._wrap_generator(self.stream.get_generator()),
                animations_manager=self.animations
            )
            
            # Setup display (clear and hide cursor)
            self.display.reset()
            
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
            self.display.reset()
            self.state_manager.clear_history()