# conversation/history.py

from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class ConversationState:
    """
    Tracks the internal conversation state.
    Internally, messages are stored as a list along with extra keys.
    When converting to a dict for the frontend, only the messages array and
    the turn number (as "turn") are exported.
    """
    messages: list = field(default_factory=list)
    turn_number: int = 0
    # Other internal keys that the backend may use but not expose to the frontend.
    system_prompt: str = None
    last_user_input: str = None
    is_silent: bool = False
    prompt_display: str = ""
    preconversation_styled: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        """
        Convert the internal state to a dict for the frontend.
        Only the "messages" key (as an array) and a "turn" key are exported.
        """
        messages_array = []
        for m in self.messages:
            if isinstance(m, dict):
                role = m.get("role")
                content = m.get("content")
            else:
                role = m.role
                content = m.content
            messages_array.append({"role": role, "content": content})
        return {"messages": messages_array, "turn": self.turn_number}

    @classmethod
    def from_dict(cls, data: dict) -> "ConversationState":
        """
        Rebuild the ConversationState from data received from the frontend.
        Only the "messages" array and "turn" number are provided.
        """
        messages_array = data.get("messages", [])
        return cls(messages=messages_array, turn_number=data.get("turn", 0))


class ConversationHistory:
    """
    Manages conversation state and JSON snapshots.
    The exported JSON only contains a "messages" array and a "turn" key.
    The backend can manage additional internal state separately.
    """

    def __init__(self, logger=None):
        self.current_state = ConversationState()
        self.state_history: dict = {}
        self.logger = logger

    def create_state_snapshot(self) -> dict:
        return self.current_state.to_dict()

    def update_state(self, **kwargs) -> None:
        """
        Update the internal state. Only keys that exist on ConversationState
        are updated. The snapshot exported contains only the "messages" and "turn" keys.
        """
        for key, value in kwargs.items():
            if hasattr(self.current_state, key):
                setattr(self.current_state, key, value)
        # Store a snapshot indexed by the current turn number.
        self.state_history[self.current_state.turn_number] = self.create_state_snapshot()
        if self.logger and hasattr(self.logger, "write_json"):
            self.logger.write_json(self.create_state_snapshot())

    def restore_state(self, turn_number: int):
        if turn_number in self.state_history:
            state_snapshot = self.state_history[turn_number]
            self.current_state = ConversationState.from_dict(state_snapshot)
            return self.current_state
        return None

    def clear_state_history(self) -> None:
        self.state_history.clear()
        self.current_state = ConversationState()
