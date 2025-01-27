# state_managers/conversation.py

from typing import List, Dict, Optional
from dataclasses import dataclass, field
import asyncio

@dataclass
class Message:
    role: str
    content: str

@dataclass
class ConversationState:
    """
    Manages conversation state and message history asynchronously.
    Handles message queuing, history, and state tracking.
    """
    system_prompt: str = ""
    messages: List[Message] = field(default_factory=list)
    last_message_silent: bool = False
    preserved_prompt: str = ""
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    
    async def add_message(self, role: str, content: str) -> None:
        """Add a message to the conversation history."""
        async with self._lock:
            self.messages.append(Message(role=role, content=content))
            
    async def get_last_user_message(self) -> Optional[str]:
        """Get the most recent user message."""
        async with self._lock:
            for msg in reversed(self.messages):
                if msg.role == "user":
                    return msg.content
        return None
        
    async def mark_silent_message(self, is_silent: bool) -> None:
        """Mark whether the last message was silent."""
        async with self._lock:
            self.last_message_silent = is_silent
            
    async def set_preserved_prompt(self, prompt: str) -> None:
        """Set the preserved prompt text."""
        async with self._lock:
            self.preserved_prompt = prompt
            
    async def get_conversation_messages(self) -> List[Dict[str, str]]:
        """Get all messages in the format expected by the API."""
        async with self._lock:
            messages = [{"role": "system", "content": self.system_prompt}] if self.system_prompt else []
            messages.extend([{"role": msg.role, "content": msg.content} for msg in self.messages])
            return messages
            
    async def clear_history(self) -> None:
        """Clear conversation history."""
        async with self._lock:
            self.messages.clear()
            self.last_message_silent = False
            self.preserved_prompt = ""
            
    @property
    def is_last_message_silent(self) -> bool:
        """Check if the last message was silent."""
        return self.last_message_silent
        
    @property
    def current_prompt(self) -> str:
        """Get the current preserved prompt."""
        return self.preserved_prompt