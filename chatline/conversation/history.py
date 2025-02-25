# conversation/history.py

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, Any, Optional, List

@dataclass
class ConversationState:
    """
    Tracks the internal conversation state.
    
    The state contains:
    - messages: The array of messages (including system prompt at index 0)
    - custom_fields: A dictionary that preserves any fields added by the backend
    
    This design focuses on a clean separation of concerns: the frontend only
    manages messages, while backend-specific fields are stored separately.
    """
    messages: list = field(default_factory=list)
    custom_fields: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """
        Convert the state to a dictionary for serialization.
        
        This returns a dictionary containing:
        - messages: The formatted messages array
        - Any backend-added fields from custom_fields
        
        Note that frontend-specific tracking (like turn counter) is not included.
        """
        # Start with just the messages
        result = {
            "messages": []
        }
        
        # Format messages array
        for m in self.messages:
            if isinstance(m, dict):
                result["messages"].append(m)
            else:
                result["messages"].append({
                    "role": m.role, 
                    "content": m.content
                })
        
        # Add any custom fields from the backend
        for key, value in self.custom_fields.items():
            result[key] = value
        
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "ConversationState":
        """
        Rebuild the ConversationState from a dictionary.
        
        This extracts the 'messages' array and places any other fields
        into the custom_fields dictionary.
        """
        # Make a copy to avoid modifying the input
        state_data = data.copy()
        
        # Extract known fields
        messages = state_data.pop("messages", [])
        
        # Any remaining fields go into custom_fields
        custom_fields = state_data
        
        # Return a new state instance
        return cls(
            messages=messages,
            custom_fields=custom_fields
        )


class ConversationHistory:
    """
    Manages conversation state history with index-based storage.
    
    This class maintains a history of conversation states, indexed by
    an internal counter rather than relying on turn numbers from the state.
    This creates a clean separation between frontend tracking and state data.
    """

    def __init__(self, logger=None):
        self.current_state = ConversationState()
        self.state_history: List[dict] = []  # Array-based history instead of dict
        self.logger = logger
        self._creation_time = datetime.now().isoformat()

    def create_state_snapshot(self) -> dict:
        """Create a dictionary representation of the current state."""
        return self.current_state.to_dict()

    def update_state(self, **kwargs) -> None:
        """
        Update the internal state with any provided fields.
        
        Messages are updated directly, while other fields go into custom_fields.
        """
        # Handle messages directly if provided
        if "messages" in kwargs:
            self.current_state.messages = kwargs.pop("messages")
        
        # Handle any custom fields
        for key, value in kwargs.items():
            self.current_state.custom_fields[key] = value
        
        # Store a snapshot in the history array
        self.state_history.append(self.create_state_snapshot())
        
        # Log the updated state
        if self.logger and hasattr(self.logger, "write_json"):
            self.logger.write_json(self.create_state_snapshot())

    def get_latest_state_index(self) -> int:
        """Get the index of the latest state in history."""
        return len(self.state_history) - 1

    def restore_state_by_index(self, index: int) -> Optional[ConversationState]:
        """
        Restore state from history based on index.
        
        Args:
            index: Zero-based index into the state history
            
        Returns:
            The restored state or None if index is invalid
        """
        if 0 <= index < len(self.state_history):
            state_snapshot = self.state_history[index]
            self.current_state = ConversationState.from_dict(state_snapshot)
            
            # Truncate history to this point
            self.state_history = self.state_history[:index + 1]
            
            return self.current_state
        return None

    def clear_state_history(self) -> None:
        """Clear all state history and reset to initial state."""
        self.state_history.clear()
        self.current_state = ConversationState()