# conversation/messages.py

from dataclasses import dataclass

@dataclass
class Message:
    """
    Represents a single message in the conversation.
    """
    role: str
    content: str
    turn_number: int = 0


class ConversationMessages:
    """
    Manages conversation messages.
    """
    def __init__(self):
        self.messages: list[Message] = []

    def add_message(self, role: str, content: str, turn_number: int) -> None:
        """Append a new message to the history."""
        self.messages.append(Message(role, content, turn_number))

    async def get_messages(self, system_prompt: str = None) -> list[dict]:
        """
        Get the message history as a list of dictionaries.
        If a system prompt is provided, it is prepended.
        """
        base_messages = [{"role": m.role, "content": m.content} for m in self.messages]
        if system_prompt:
            return [{"role": "system", "content": system_prompt}] + base_messages
        return base_messages

    def remove_last_n_messages(self, n: int) -> None:
        """Remove the last n messages."""
        if n <= len(self.messages):
            self.messages = self.messages[:-n]
        else:
            self.messages = []
