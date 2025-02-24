# conversation/history.py

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, Any

@dataclass
class ConversationState:
    """
    Tracks the internal conversation state.
    
    The state contains:
    - messages: The array of messages (including system prompt at index 0)
    - turn_number: The current turn in the conversation
    - custom_fields: A dictionary that preserves any fields added by the backend
    
    All UI-specific state has been moved to the UI components.
    """
    messages: list = field(default_factory=list)
    turn_number: int = 0
    custom_fields: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """
        Convert the state to a dictionary for serialization.
        
        This creates a dictionary with:
        - Core fields (messages, turn_number)
        - Any custom fields added by the backend
        """
        # Start with the core fields
        result = {
            "messages": [],
            "turn_number": self.turn_number
        }
        
        # Format messages array
        for m in self.messages:
            if isinstance(m, dict):
                result["messages"].append(m)
            else:
                result["messages"].append({
                    "role": m.role, 
                    "content": m.content, 
                    "turn_number": m.turn_number
                })
        
        # Add any custom fields
        for key, value in self.custom_fields.items():
            result[key] = value
        
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "ConversationState":
        """
        Rebuild the ConversationState from a dictionary.
        
        This handles both:
        - Core fields (messages, turn_number)
        - Any additional fields from the backend
        """
        # Make a copy to avoid modifying the input
        state_data = data.copy()
        
        # Extract core fields
        messages = state_data.pop("messages", [])
        turn_number = state_data.pop("turn_number", 0)
        
        # Remove obsolete fields for backward compatibility
        old_fields = [
            "system_prompt", 
            "last_user_input", 
            "is_silent", 
            "prompt_display", 
            "preconversation_styled",
            "timestamp"
        ]
        for old_field in old_fields:
            if old_field in state_data:
                state_data.pop(old_field)
        
        # Any remaining fields go into custom_fields
        custom_fields = state_data
        
        return cls(
            messages=messages,
            turn_number=turn_number,
            custom_fields=custom_fields
        )


class ConversationHistory:
    """
    Manages conversation state and JSON snapshots.
    """

    def __init__(self, logger=None):
        self.current_state = ConversationState()
        self.state_history: dict = {}
        self.logger = logger

    def create_state_snapshot(self) -> dict:
        """Create a dictionary representation of the current state."""
        return self.current_state.to_dict()

    def update_state(self, **kwargs) -> None:
        """
        Update the internal state with any provided fields.
        
        This method handles:
        - Core fields (messages, turn_number) that update ConversationState directly
        - Any other fields that go into custom_fields
        """
        # Handle core fields explicitly
        core_fields = {"messages", "turn_number"}
        
        # Update direct fields first
        for key in core_fields:
            if key in kwargs:
                setattr(self.current_state, key, kwargs[key])
        
        # Handle custom fields
        for key, value in kwargs.items():
            if key not in core_fields:
                self.current_state.custom_fields[key] = value
        
        # Store a snapshot indexed by the current turn number
        self.state_history[self.current_state.turn_number] = self.create_state_snapshot()
        
        # Log the updated state if a logger is available
        if self.logger and hasattr(self.logger, "write_json"):
            self.logger.write_json(self.create_state_snapshot())

    def restore_state(self, turn_number: int):
        """Restore state from history based on turn number."""
        if turn_number in self.state_history:
            state_snapshot = self.state_history[turn_number]
            self.current_state = ConversationState.from_dict(state_snapshot)
            return self.current_state
        return None

    def clear_state_history(self) -> None:
        """Clear all state history and reset to initial state."""
        self.state_history.clear()
        self.current_state = ConversationState()