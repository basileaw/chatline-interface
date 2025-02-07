# interface.py

import logging
from typing import Optional, Dict, Callable
from .display import Display
from .conversation import Conversation
from .stream import EmbeddedStream, RemoteStream
from .generator import generate_stream
from .logger import get_logger

class Interface:
    """
    Main interface coordinator for the chat application.
    
    Provides a clean interface for initializing and starting conversations,
    coordinating between the display, conversation, and stream components.
    """
    def __init__(
        self, 
        endpoint: Optional[str] = None, 
        generator_func: Optional[Callable] = None, 
        logging_enabled: bool = False
    ):
        """
        Initialize the interface with optional remote endpoint or custom generator.
        
        Args:
            endpoint: Optional URL for remote chat endpoint
            generator_func: Optional custom generator function
            logging_enabled: Whether to enable logging to file
        """
        self.logger = get_logger(__name__, logging_enabled)
        self._init_components(endpoint, generator_func or generate_stream)

    def _init_components(self, endpoint: Optional[str], generator_func: Callable) -> None:
        """
        Initialize all required components for the chat interface.
        
        Args:
            endpoint: Optional remote endpoint URL
            generator_func: Generator function for message streaming
        """
        try:
            # Initialize display coordinator
            self.display = Display()
            
            # Initialize appropriate stream handler
            self.stream = (RemoteStream(endpoint, logger=self.logger) 
                         if endpoint 
                         else EmbeddedStream(generator_func, logger=self.logger))
            
            # Initialize conversation with display components and stream generator
            self.conversation = Conversation(
                utilities=self.display.utilities,
                styles=self.display.styles,
                animations=self.display.animations,
                generator_func=self.stream.get_generator()
            )
            
            # Setup display
            self.display.reset()
            
        except Exception as e:
            self.logger.error(f"Initialization error: {str(e)}")
            raise

    def preface(self, text: str, color: Optional[str] = None, display_type: str = "panel") -> None:
        """
        Add preface text to be displayed before the conversation starts.
        
        Args:
            text: Text content to display
            color: Optional color for the text
            display_type: Display style ("text" or "panel")
        """
        try:
            self.conversation.preface(text, color, display_type)
            self.logger.debug(f"Added preface: {text[:50]}")
        except Exception as e:
            self.logger.error(f"Preface error: {str(e)}")
            raise

    def start(self, messages: Optional[Dict[str, str]] = None) -> None:
        """
        Start the conversation with optional initial messages.
        
        Args:
            messages: Optional dictionary containing system and user messages
        """
        try:
            self.conversation.start(messages)
        except KeyboardInterrupt:
            self.logger.info("User interrupted conversation")
        except Exception as e:
            self.logger.error(f"Start error: {str(e)}")
            raise
        finally:
            self.display.reset()