# state.py
from dataclasses import dataclass
from typing import List, Optional, Dict

@dataclass
class TerminalState:
    """Maintains terminal display state."""
    visible_content: str = ""
    previous_input: Optional[str] = None
    previous_raw: Optional[str] = None
    previous_styled: Optional[str] = None
    conversation: List[Dict] = None
    
    def __post_init__(self):
        if self.conversation is None:
            self.conversation = []
    
    def update_content(self, raw: str, styled: str, user_input: str) -> None:
        """Update terminal state with new content."""
        self.previous_raw = raw
        self.previous_styled = styled
        self.previous_input = user_input
        self.visible_content = styled
    
    def clear_content(self) -> None:
        """Clear visible content while preserving history."""
        self.visible_content = ""