# conversation/history.py

from dataclasses import dataclass, field, asdict
from datetime import datetime

@dataclass
class ConversationState:
    """
    Tracks the internal conversation state.
    This state data is shared between frontend and backend, allowing
    both to add, modify, or utilize any fields as needed.
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
        """
        Convert the entire state to a dictionary, preserving all fields.
        This allows backends to access and modify any part of the state.
        """
        # First convert all dataclass fields to a dictionary
        state_dict = asdict(self)
        
        # Ensure the messages are properly formatted
        messages_array = []
        for m in self.messages:
            if isinstance(m, dict):
                messages_array.append(m)
            else:
                messages_array.append({"role": m.role, "content": m.content, "turn_number": m.turn_number})
        
        # Replace the messages with properly formatted ones
        state_dict["messages"] = messages_array
        
        return state_dict

    @classmethod
    def from_dict(cls, data: dict) -> "ConversationState":
        """
        Rebuild the ConversationState from data received from the backend.
        This preserves all fields that were sent.
        """
        # Make a copy to avoid modifying the input
        state_data = data.copy()
        
        # Extract and convert messages if they exist
        if "messages" in state_data:
            messages = state_data.pop("messages")
            # Don't convert messages yet, as the ConversationState expects a list
            # The Message objects will be created when needed in ConversationMessages
        else:
            messages = []
        
        # Create the state with all the fields
        return cls(messages=messages, **state_data)


class ConversationHistory:
    """
    Manages conversation state and JSON snapshots.
    The entire state is preserved when communicating with the backend.
    """

    def __init__(self, logger=None):
        self.current_state = ConversationState()
        self.state_history: dict = {}
        self.logger = logger

    def create_state_snapshot(self) -> dict:
        return self.current_state.to_dict()

    def update_state(self, **kwargs) -> None:
        """
        Update the internal state with any provided fields.
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