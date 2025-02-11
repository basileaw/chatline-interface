# display/__init__.py

from .terminal import DisplayTerminal
from .style import DisplayStyle
from .animations import DisplayAnimations

class Display:
    """
    Coordinates terminal display components in a hierarchical structure.
    
    Component Hierarchy:
    DisplayTerminal (base) → DisplayStyle → DisplayAnimations
    """
    def __init__(self):
        """Initialize components in dependency order."""
        self.terminal = DisplayTerminal()
        self.style = DisplayStyle(terminal=self.terminal)
        self.animations = DisplayAnimations(terminal=self.terminal, style=self.style)

    @property
    def io(self):
        """
        Backward compatibility property for code expecting display.io.
        Delegates operations to terminal and style components.
        """
        return DisplayIOAdapter(self.terminal, self.style)

class DisplayIOAdapter:
    """Adapter class that provides the old IO interface using new components."""
    
    def __init__(self, terminal, style):
        self.terminal = terminal
        self.style = style

    def format_prompt(self, text: str) -> str:
        """Format a prompt based on user input."""
        end_char = text[-1] if text.endswith(('?', '!')) else '.'
        return f"> {text.rstrip('?.!')}{end_char * 3}"

    async def clear(self) -> None:
        """Clear the display."""
        self.terminal.clear_screen()
        await self.terminal.yield_to_event_loop()

    async def write_lines(self, lines, newline: bool = True) -> None:
        """Write multiple lines to the display."""
        for line in lines:
            self.terminal.write(line, newline=newline)
        await self.terminal.yield_to_event_loop()

    async def write_prompt(self, prompt: str, style_name: str = None) -> None:
        """Write a prompt with optional style."""
        if style_name:
            self.terminal.write(self.style.get_format(style_name))
        self.terminal.write(prompt)
        if style_name:
            self.terminal.write(self.style.get_format('RESET'))
        await self.terminal.yield_to_event_loop()

    async def update_display(
        self,
        content: str = None,
        prompt: str = None,
        preserve_cursor: bool = False
    ) -> None:
        """Update display content and prompt."""
        if not preserve_cursor:
            self.terminal.hide_cursor()
        await self.clear()
        if content:
            await self.write_lines([content], bool(prompt))
        if prompt:
            await self.write_prompt(prompt)
        if not preserve_cursor:
            self.terminal.hide_cursor()

__all__ = ['Display']