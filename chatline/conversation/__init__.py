# conversation/__init__.py

from .actions import ConversationActions
from .history import ConversationHistory
from .messages import ConversationMessages
from .preface import ConversationPreface


class Conversation:
    """Container for conversation components and actions."""

    def __init__(
        self,
        display,
        stream,
        logger,
        conclusion_string=None,
        loading_message=None,
        interface_config=None,
        save_directory="./saved_conversations/",
    ):
        # Provide logger so history can do logger.write_json(...)
        self.history = ConversationHistory(
            logger=logger, interface_config=interface_config
        )
        self.messages = ConversationMessages()
        self.preface = ConversationPreface()
        self.actions = ConversationActions(
            display=display,
            stream=stream,
            history=self.history,
            messages=self.messages,
            preface=self.preface,
            logger=logger,
            conclusion_string=conclusion_string,
            loading_message=loading_message,
            save_directory=save_directory,
        )


__all__ = ["Conversation"]
