# interface.py

import logging
import os
from typing import Optional, Dict, Any, Callable
from .terminal import Terminal
from .conversation import Conversation, StateManager  # Updated import
from .animations import Animations
from .styles import Styles
from .stream import EmbeddedStream, RemoteStream
from .generator import generate_stream

class Interface:
    def __init__(self, 
                 endpoint: Optional[str] = None, 
                 generator_func: Optional[Callable] = None):
        """Initialize Interface with optional endpoint or generator function"""
        self._setup_logging()
        if not endpoint and not generator_func:
            generator_func = generate_stream
        self._init_components(endpoint, generator_func)

    def _setup_logging(self) -> None:
        """Setup logging configuration"""
        log_dir = os.path.join(os.path.dirname(__file__), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s',
            filename=os.path.join(log_dir, 'chat_debug.log')
        )
        self.logger = logging.getLogger(__name__)

    def _init_components(self, 
                        endpoint: Optional[str], 
                        generator_func: Optional[Callable]) -> None:
        """Initialize all components with proper state management"""
        try:
            # Terminal and styles initialization
            self.terminal = Terminal(styles=None)
            self.styles = Styles(terminal=self.terminal)
            self.terminal.styles = self.styles
            
            # Animations setup
            self.animations = Animations(
                terminal=self.terminal,
                styles=self.styles
            )
            
            # Create state manager
            self.state_manager = StateManager(logger=self.logger)
            
            # Stream initialization with state management
            if endpoint:
                self.logger.info("Using remote endpoint: %s", endpoint)
                self.stream = RemoteStream(endpoint, logger=self.logger)
            else:
                self.logger.info("Using embedded stream")
                self.stream = EmbeddedStream(generator_func, logger=self.logger)
                
            self.generator = self._wrap_generator(self.stream.get_generator())
            
            # Conversation setup with state management
            self.conversation = Conversation(
                terminal=self.terminal,
                generator_func=self.generator,
                styles=self.styles,
                animations_manager=self.animations
            )
            
            self.terminal._clear_screen()
            self.terminal._hide_cursor()
            
        except Exception as e:
            self.logger.error("Init error: %s", str(e))
            raise

    def _wrap_generator(self, generator_func: Callable) -> Callable:
        """Wrap generator to include state management"""
        async def wrapped_generator(messages: list, **kwargs: Any):
            try:
                # Get current state from conversation
                current_state = self.state_manager.get_current_state()
                
                # Pass state to generator
                async for chunk in generator_func(
                    messages, 
                    state=current_state.to_dict() if current_state else None,
                    **kwargs
                ):
                    yield chunk
                    
            except Exception as e:
                self.logger.error("Generator error: %s", str(e))
                yield f"Error during generation: {str(e)}"
        
        return wrapped_generator

    def preface(self, 
                text: str, 
                color: Optional[str] = None, 
                display_type: str = "panel") -> None:
        """Add preface text with styling"""
        try:
            self.conversation.preface(text, color, display_type)
            self.logger.debug("Added preface: %s", text[:50])
        except Exception as e:
            self.logger.error("Preface error: %s", str(e))
            raise

    def start(self, messages: Optional[Dict[str, str]] = None) -> None:
        """Start the chat interface"""
        try:
            self.conversation.start(messages)
        except KeyboardInterrupt:
            self.logger.info("User interrupted")
            self.terminal._show_cursor()
        except Exception as e:
            self.logger.error("Start error: %s", str(e))
            self.terminal._show_cursor()
            raise
        finally:
            # Clear state on exit
            self.state_manager.clear_history()