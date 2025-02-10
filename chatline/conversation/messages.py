# conversation/messages.py

from dataclasses import dataclass

@dataclass
class Message:
    """A conversation message."""
    role: str
    content: str
    turn_number: int = 0

class ConversationMessages:
    """Handles conversation messages."""
    def __init__(self):
        self.messages: list[Message] = []

    def add_message(self, role: str, content: str, turn_number: int) -> None:
        """Add a message to the history."""
        self.messages.append(Message(role, content, turn_number))

    async def get_messages(self, system_prompt: str = None) -> list[dict]:
        """Return messages as dicts; prepend system prompt if provided."""
        base_messages = [{"role": m.role, "content": m.content} for m in self.messages]
        return [{"role": "system", "content": system_prompt}] + base_messages if system_prompt else base_messages

    def remove_last_n_messages(self, n: int) -> None:
        """Remove the last n messages."""
        self.messages = self.messages[:-n] if n <= len(self.messages) else []
