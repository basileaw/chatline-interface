# conversation/__init__.py

from .actions import ConversationActions
from .history import ConversationHistory
from .messages import ConversationMessages

class Conversation:
    """Container for conversation components and actions."""
    def __init__(self, display, stream, logger):
        self.history = ConversationHistory()
        self.messages = ConversationMessages()
        self.actions = ConversationActions(
            display=display, 
            stream=stream, 
            history=self.history, 
            messages=self.messages,
            logger=logger
        )

__all__ = ['Conversation']
