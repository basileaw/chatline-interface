# display/style/strategies.py

from rich.panel import Panel
from rich.align import Align
from rich.console import Console
from typing import Dict, Union
from .definitions import StyleDefinitions

class StyleStrategies:
    """
    Handles different display formatting strategies, working directly with
    terminal output and style definitions.
    """
    def __init__(self, definitions: StyleDefinitions, terminal):
        """
        Initialize with style definitions and terminal dependencies.
        
        Args:
            definitions: StyleDefinitions for style rules and patterns
            terminal: DisplayTerminal instance for output operations
        """
        self.definitions = definitions
        self.terminal = terminal
        self.console = Console(force_terminal=True, color_system="truecolor", record=True)

    def format(self, content: Union[Dict, object], style: str = "text") -> str:
        """
        Format content according to specified style.
        
        Args:
            content: Content to format (dict or object with text/color attributes)
            style: Style to apply ("panel" or "text")
            
        Returns:
            Formatted text string
        """
        if style == "panel":
            return self._format_panel(content)
        return self._format_text(content)

    def get_visible_length(self, text: str) -> int:
        """
        Return visible length of text, accounting for terminal width.
        
        Args:
            text: Text to measure
            
        Returns:
            Visible length considering terminal constraints
        """
        # Use terminal width as constraint
        return min(len(text), self.terminal.width)

    def _format_text(self, content: Union[Dict, object]) -> str:
        """
        Format as simple text with newline.
        
        Args:
            content: Text content to format
            
        Returns:
            Formatted text string
        """
        text = content["text"] if isinstance(content, dict) else content.text
        return text + "\n"

    def _format_panel(self, content: Union[Dict, object]) -> str:
        """
        Format as centered Rich panel with proper styling.
        
        Args:
            content: Content to format with optional color
            
        Returns:
            Formatted panel string
        """
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
                    expand=True,
                    width=self.terminal.width  # Use terminal width for panel
                )
            )
        return capture.get()