# conversation/history.py

import copy
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class ConversationState:
    """
    Tracks the current conversation state.
    Typically 'messages' is a list of dicts or Message objects.
    """
    messages: list = field(default_factory=list)
    turn_number: int = 0
    system_prompt: str = None
    last_user_input: str = None
    is_silent: bool = False
    prompt_display: str = ""
    preconversation_styled: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}

    @classmethod
    def from_dict(cls, data: dict) -> 'ConversationState':
        return cls(**data)


class ConversationHistory:
    """
    Manages conversation state and triggers JSON dumps
    via logger.write_json(...)
    """

    def __init__(self, logger=None):
        self.current_state = ConversationState()
        self.state_history: dict = {}
        self.logger = logger

    def create_state_snapshot(self) -> dict:
        return copy.deepcopy(self.current_state.to_dict())

    def update_state(self, **kwargs) -> None:
        """
        Update the current state and store a snapshot.
        Then dump the entire conversation to JSON (if logger has json_history_path).
        """
        # Standard update
        for key, value in kwargs.items():
            if hasattr(self.current_state, key):
                setattr(self.current_state, key, value)

        self.state_history[self.current_state.turn_number] = self.create_state_snapshot()

        # Write out JSON if our logger supports it
        if self.logger and hasattr(self.logger, "write_json"):
            # Example: build a minimal array of role/content/turn_number
            data = []
            for msg in self.current_state.messages:
                # If each msg is a dict
                data.append({
                    "role": msg.get("role"),
                    "content": msg.get("content"),
                    "turn_number": msg.get("turn_number", 0)
                })
            self.logger.write_json(data)

    def restore_state(self, turn_number: int):
        if turn_number in self.state_history:
            self.current_state = ConversationState.from_dict(self.state_history[turn_number])
            return self.current_state
        return None

    def clear_state_history(self) -> None:
        self.state_history.clear()
        self.current_state = ConversationState()
