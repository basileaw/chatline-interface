# conversation/history.py

import copy
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class ConversationState:
    """
    Tracks the current conversation state.
    messages is typically a list of dicts: [{"role": "...", "content": "...", ...}, ...]
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
        """Return state as a dict."""
        return {k: v for k, v in self.__dict__.items()}

    @classmethod
    def from_dict(cls, data: dict) -> 'ConversationState':
        """Create a state instance from a dict."""
        return cls(**data)


class ConversationHistory:
    """
    Manages conversation state and its history. 
    Also triggers JSON dumps via logger.write_json().
    """

    def __init__(self, logger=None):
        self.current_state = ConversationState()
        self.state_history: dict = {}
        self.logger = logger  # We'll call logger.write_json(...) in update_state

    def create_state_snapshot(self) -> dict:
        """Return a deep copy of the current state as a dict."""
        return copy.deepcopy(self.current_state.to_dict())

    def update_state(self, **kwargs) -> None:
        """
        Update the current state and store a snapshot.
        Then dump the entire conversation to JSON (if logger has a json_history_path).
        """
        # Standard update
        for key, value in kwargs.items():
            if hasattr(self.current_state, key):
                setattr(self.current_state, key, value)

        self.state_history[self.current_state.turn_number] = self.create_state_snapshot()

        # Now write JSON if our logger supports it
        if self.logger and hasattr(self.logger, "write_json"):
            # Build a minimal JSON structure from the entire conversation
            # For example, just the role/content/turn_number for each message:
            data = []
            for msg in self.current_state.messages:
                # 'msg' is presumably a dict with keys "role", "content", and "turn_number"
                data.append({
                    "role": msg.get("role"),
                    "content": msg.get("content"),
                    "turn_number": msg.get("turn_number", 0)
                })
            self.logger.write_json(data)

    def restore_state(self, turn_number: int):
        """Restore state from a given turn number."""
        if turn_number in self.state_history:
            self.current_state = ConversationState.from_dict(self.state_history[turn_number])
            return self.current_state
        return None

    def clear_state_history(self) -> None:
        """Reset state history and current state."""
        self.state_history.clear()
        self.current_state = ConversationState()
