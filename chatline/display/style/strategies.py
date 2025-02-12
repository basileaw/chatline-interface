# display/style/strategies.py

from rich.panel import Panel
from rich.align import Align
from rich.console import Console
from typing import Dict, Union

class StyleStrategies:
    """Manage display formatting strategies using terminal and injected style definitions."""
    def __init__(self, definitions, terminal):
        """Initialize with injected style definitions and terminal instance."""
        self.definitions = definitions
        self.terminal = terminal
        self.console = Console(force_terminal=True, color_system="truecolor", record=True)

    def format(self, content: Union[Dict, object], style: str = "text") -> str:
        """Format content as 'panel' or 'text' and return the formatted string."""
        if style == "panel":
            return self._format_panel(content)
        return self._format_text(content)

    def get_visible_length(self, text: str) -> int:
        """Return visible text length limited by terminal width."""
        return min(len(text), self.terminal.width)

    def _format_text(self, content: Union[Dict, object]) -> str:
        """Return simple text with a trailing newline."""
        text = content["text"] if isinstance(content, dict) else content.text
        return text + "\n"

    def _format_panel(self, content: Union[Dict, object]) -> str:
        """Return content formatted as a centered Rich panel."""
        text = content["text"] if isinstance(content, dict) else content.text
        color = (content.get("color") if isinstance(content, dict)
                else getattr(content, "color", None)) or "white"
        title = (content.get("title") if isinstance(content, dict)
                else getattr(content, "title", None))
        border_color = (content.get("border_color") if isinstance(content, dict)
                    else getattr(content, "border_color", None)) or "white"
        
        with self.console.capture() as capture:
            self.console.print(
                Panel(
                    Align.center(text.rstrip()),
                    title=title,
                    title_align="right",
                    border_style=border_color,  # Use the dynamic border_color
                    style=color,
                    padding=(1, 2),
                    expand=True,
                    width=self.terminal.width
                )
            )
        return capture.get()