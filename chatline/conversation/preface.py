# conversation/preface.py

from typing import List
from dataclasses import dataclass

@dataclass
class PrefaceContent:
    """Container for preface content and its display properties."""
    text: str
    color: str = None
    display_type: str = "panel"
    title: str = None
    border_color: str = None

class ConversationPreface:
    """Manages preface content and styling for conversations."""
    def __init__(self):
        self.content_items: List[PrefaceContent] = []
        self.styled_content: str = ""
    
    def add_content(self, text: str, color: str = None, display_type: str = "panel", 
                title: str = None, border_color: str = None) -> None:
        """Add new preface content."""
        content = PrefaceContent(text, color, display_type, title, border_color)
        self.content_items.append(content)
    
    def clear(self) -> None:
        """Clear all preface content."""
        self.content_items.clear()
        self.styled_content = ""
    
    async def format_content(self, style) -> str:
        """Format all preface content using provided style engine."""
        if not self.content_items:
            return ""
            
        styled_parts = []
        for content in self.content_items:
            style.set_output_color(content.color)
            _, styled = await style.write_styled(style.strategies.format(content, content.display_type))
            styled_parts.append(styled)
            
        self.styled_content = ''.join(styled_parts)
        return self.styled_content