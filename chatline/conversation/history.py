# conversation/history.py

import copy
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class ConversationState:
    """
    Maintains the current state of the conversation.
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
        """Convert state to dictionary for storage."""
        return {k: v for k, v in self.__dict__.items()}

    @classmethod
    def from_dict(cls, data: dict) -> 'ConversationState':
        """Create state instance from dictionary."""
        return cls(**data)


class ConversationHistory:
    """
    Manages conversation state and state history.
    """
    def __init__(self):
        self.current_state = ConversationState()
        self.state_history: dict = {}

    def create_state_snapshot(self) -> dict:
        """Create a deep copy of the current state."""
        return copy.deepcopy(self.current_state.to_dict())

    def update_state(self, **kwargs) -> None:
        """
        Update the current state with new values and store a snapshot.
        """
        for key, value in kwargs.items():
            if hasattr(self.current_state, key):
                setattr(self.current_state, key, value)
        self.state_history[self.current_state.turn_number] = self.create_state_snapshot()

    def restore_state(self, turn_number: int):
        """
        Restore state from a specific turn number.
        """
        if turn_number in self.state_history:
            self.current_state = ConversationState.from_dict(self.state_history[turn_number])
            return self.current_state
        return None

    def clear_state_history(self) -> None:
        """Clear the state history and reset the current state."""
        self.state_history.clear()
        self.current_state = ConversationState()
