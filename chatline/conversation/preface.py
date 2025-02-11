# conversation/preface.py

from typing import List
from dataclasses import dataclass

@dataclass
class PrefaceContent:
    """Container for preface content and its display properties."""
    text: str
    color: str = None
    display_type: str = "panel"

class ConversationPreface:
    """Manages preface content and styling for conversations."""
    def __init__(self):
        self.content_items: List[PrefaceContent] = []
        self.styled_content: str = ""
    
    def add_content(self, text: str, color: str = None, display_type: str = "panel") -> None:
        """Add new preface content."""
        content = PrefaceContent(text, color, display_type)
        self.content_items.append(content)
    
    def clear(self) -> None:
        """Clear all preface content."""
        self.content_items.clear()
        self.styled_content = ""
    
    async def format_content(self, styles) -> str:
        """Format all preface content using provided style strategies."""
        if not self.content_items:
            return ""
            
        styled_parts = []
        for content in self.content_items:
            strategy = styles.create_display_strategy(content.display_type)
            styles.set_output_color(content.color)
            _, styled = await styles.write_styled(strategy.format(content))
            styled_parts.append(styled)
            
        self.styled_content = ''.join(styled_parts)
        return self.styled_content