# conversation_state.py

from dataclasses import dataclass, field
from typing import List, Dict, Optional
import copy
import json
import logging
from datetime import datetime

@dataclass
class ConversationState:
    messages: List[Dict[str, str]] = field(default_factory=list)
    turn_number: int = 0
    system_prompt: Optional[str] = None
    last_user_input: Optional[str] = None
    is_silent: bool = False
    prompt_display: str = ""
    preconversation_styled: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        """Convert state to dictionary for storage"""
        return {
            'messages': self.messages,
            'turn_number': self.turn_number,
            'system_prompt': self.system_prompt,
            'last_user_input': self.last_user_input,
            'is_silent': self.is_silent,
            'prompt_display': self.prompt_display,
            'preconversation_styled': self.preconversation_styled,
            'timestamp': self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ConversationState':
        """Create state from dictionary"""
        return cls(**data)

    def create_snapshot(self) -> Dict:
        """Create a deep copy snapshot of current state"""
        return copy.deepcopy(self.to_dict())

class StateManager:
    def __init__(self, logger=None):
        self.current_state = ConversationState()
        self.state_history: Dict[int, Dict] = {}  # turn_number -> state_snapshot
        self.logger = logger or logging.getLogger(__name__)
        
    def update_state(self, **kwargs) -> None:
        """Update current state with new values"""
        for key, value in kwargs.items():
            if hasattr(self.current_state, key):
                setattr(self.current_state, key, value)
        
        # Create snapshot after update
        self._create_snapshot()
        
    def _create_snapshot(self) -> None:
        """Store snapshot of current state"""
        self.state_history[self.current_state.turn_number] = \
            self.current_state.create_snapshot()
            
    def restore_state(self, turn_number: int) -> Optional[ConversationState]:
        """Restore state from history"""
        if turn_number in self.state_history:
            state_dict = self.state_history[turn_number]
            self.current_state = ConversationState.from_dict(state_dict)
            return self.current_state
        return None
    
    def get_current_state(self) -> ConversationState:
        """Get current state"""
        return self.current_state
    
    def clear_history(self) -> None:
        """Clear state history"""
        self.state_history.clear()
        self.current_state = ConversationState()