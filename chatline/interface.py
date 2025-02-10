# interface.py

from typing import Optional, Dict, Any
from .display import Display
from .conversation import Conversation
from .stream import Stream
from .logger import get_logger

class Interface:
    """
    Main interface coordinator for the chat application.
    
    Provides a clean interface for initializing and starting conversations,
    coordinating between the display, conversation, and stream components
    while managing system-level concerns like logging.
    """
    def __init__(
        self, 
        endpoint: Optional[str] = None, 
        logging_enabled: bool = False
    ):
        """
        Initialize the interface.
        
        Args:
            endpoint: Optional URL for remote endpoint. If not provided,
                     runs with embedded message generation.
            logging_enabled: Whether to enable logging to file
        """
        self.logger = get_logger(__name__, logging_enabled)
        self._init_components(endpoint)

    def _init_components(self, endpoint: Optional[str]) -> None:
        """
        Initialize all required components for the chat interface.
        
        This method handles the proper initialization order and error handling
        for all major system components.
        
        Args:
            endpoint: Optional remote endpoint URL
        """
        try:
            # Initialize display system
            self.display = Display()
            
            # Initialize stream (type handled internally by Stream class)
            self.stream = Stream.create(endpoint, logger=self.logger)
            
            # Initialize conversation with display components
            self.conversation = Conversation(
                display=self.display,
                stream=self.stream
            )
            
            # Ensure clean initial state
            self.display.terminal.reset()
            
        except Exception as e:
            self.logger.error(f"Initialization error: {str(e)}")
            raise

    def preface(
        self,
        text: str,
        color: Optional[str] = None,
        display_type: str = "panel"
    ) -> None:
        """
        Add preface text to be displayed before the conversation starts.
        
        Args:
            text: Text content to display
            color: Optional color for the text
            display_type: Display style ("text" or "panel")
            
        Raises:
            Exception: If there's an error adding the preface
        """
        try:
            self.conversation.preface(text, color, display_type)
            self.logger.debug(f"Added preface: {text[:50]}")
        except Exception as e:
            self.logger.error(f"Preface error: {str(e)}")
            raise

    def start(self, messages: Dict[str, str]) -> None:
        """
        Start the conversation with the provided messages.
        
        This method handles the main conversation loop, including proper
        cleanup on exit or error.
        
        Args:
            messages: Dictionary containing 'system' and 'user' messages
            
        Raises:
            KeyboardInterrupt: If user interrupts the conversation
            Exception: For other errors during conversation
        """
        try:
            self.conversation.start(messages)
        except KeyboardInterrupt:
            self.logger.info("User interrupted conversation")
        except Exception as e:
            self.logger.error(f"Start error: {str(e)}")
            raise
        finally:
            # Always ensure we reset the display state
            self.display.terminal.reset()