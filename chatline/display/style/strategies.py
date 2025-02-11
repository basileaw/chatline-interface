# style/strategies.py

from rich.panel import Panel
from rich.align import Align
from rich.console import Console
from typing import Dict, Union

class DisplayStrategy:
    """Base class for display strategies."""
    def format(self, content: Union[Dict, object]) -> str:
        pass

    def get_visible_length(self, text: str) -> int:
        pass

class TextDisplayStrategy(DisplayStrategy):
    """Simple text display with newline."""
    def __init__(self, application):
        self.application = application

    def format(self, content: Union[Dict, object]) -> str:
        text = content["text"] if isinstance(content, dict) else content.text
        return text + "\n"

    def get_visible_length(self, text: str) -> int:
        return self.application.get_visible_length(text)

class PanelDisplayStrategy(DisplayStrategy):
    """Centered Rich panel display."""
    def __init__(self, application):
        self.application = application
        self.console = Console(force_terminal=True, color_system="truecolor", record=True)

    def format(self, content: Union[Dict, object]) -> str:
        # Handle both dict and object-style content
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

    def get_visible_length(self, text: str) -> int:
        return self.application.get_visible_length(text) + 4