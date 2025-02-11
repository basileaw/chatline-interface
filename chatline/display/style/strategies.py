# style/strategies.py

from rich.panel import Panel
from rich.align import Align
from rich.console import Console
from typing import Dict, Union

class StyleStrategy:
    """Handles all display formatting strategies."""
    def __init__(self):
        self.application = None
        self.console = Console(force_terminal=True, color_system="truecolor", record=True)

    def set_application(self, application):
        """Set the application reference after initialization."""
        self.application = application

    def format(self, content: Union[Dict, object], style: str = "text") -> str:
        """Format content according to specified style."""
        if style == "panel":
            return self._format_panel(content)
        return self._format_text(content)

    def get_visible_length(self, text: str) -> int:
        """Return visible length of text."""
        if not self.application:
            return len(text)
        return self.application.get_visible_length(text)

    def _format_text(self, content: Union[Dict, object]) -> str:
        """Format as simple text with newline."""
        text = content["text"] if isinstance(content, dict) else content.text
        return text + "\n"

    def _format_panel(self, content: Union[Dict, object]) -> str:
        """Format as centered Rich panel."""
        text = content["text"] if isinstance(content, dict) else content.text
        color = (content.get("color") if isinstance(content, dict) 
                else getattr(content, "color", None)) or "on grey23"

        with self.console.capture() as capture:
            self.console.print(
                Panel(
                    Align.center(text.rstrip()),
                    title="Baze Inc.",
                    title_align="right",
                    border_style="dim yellow",
                    style=color,
                    padding=(1, 2),
                    expand=True
                )
            )
        return capture.get()