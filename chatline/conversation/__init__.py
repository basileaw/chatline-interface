# conversation/__init__.py

import asyncio
import logging
from .actions import ConversationActions
from .history import ConversationHistory
from .messages import ConversationMessages

class Conversation:
    """
    Coordinates conversation components.
    
    Exposes only the public methods 'start' and 'preface'.
    """
    def __init__(self, display, stream):
        self.display = display
        self._history = ConversationHistory()
        self._messages = ConversationMessages()
        self._actions = ConversationActions(display, stream, self._history, self._messages)
        self._logger = logging.getLogger(__name__)

    def preface(self, text: str, color: str = None, display_type: str = "panel") -> None:
        """
        Add preface content to the conversation.
        """
        self._actions.add_preface(text, color, display_type)

    def start(self, messages: dict) -> None:
        """
        Start the conversation.
        
        The messages dictionary must include both 'system' and 'user' keys.
        """
        if not messages or 'system' not in messages or 'user' not in messages:
            raise ValueError("Both system and user messages are required")
        try:
            asyncio.run(self._actions.run_conversation(messages['system'], messages['user']))
        except KeyboardInterrupt:
            print("\nExiting...")
        finally:
            self.display.terminal.reset()


__all__ = ['Conversation']