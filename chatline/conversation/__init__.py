# conversation/__init__.py

from .actions import ConversationActions
from .history import ConversationHistory
from .messages import ConversationMessages
from .preface import ConversationPreface

class Conversation:
    """Container for conversation components and actions."""

    def __init__(self, display, stream, logger):
        # Provide logger so history can do logger.write_json(...)
        self.history = ConversationHistory(logger=logger)
        self.messages = ConversationMessages()
        self.preface = ConversationPreface()
        self.actions = ConversationActions(
            display=display,
            stream=stream,
            history=self.history,
            messages=self.messages,
            preface=self.preface,
            logger=logger
        )

__all__ = ['Conversation']
