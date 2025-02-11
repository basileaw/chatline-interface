# display/style/engine.py

import re
import sys
import asyncio
from io import StringIO
from rich.style import Style
from rich.console import Console
from typing import Dict, List, Optional, Tuple, Union
from .definitions import StyleDefinitions

class StyleEngine:
    """
    Core styling engine that processes and applies text styles.
    
    This class handles the actual styling operations, working with the terminal
    for output while using StyleDefinitions and StyleStrategies for styling rules.
    It processes text chunks, manages active styles, and coordinates styling state.
    """
    def __init__(self, terminal, definitions: StyleDefinitions, strategies):
        """
        Initialize the style engine with its dependencies.
        
        Args:
            terminal: DisplayTerminal instance for output operations
            definitions: StyleDefinitions for style rules and patterns
            strategies: StyleStrategies for different styling approaches
        """
        self.terminal = terminal
        self.definitions = definitions
        self.strategies = strategies
        
        # Initialize styling state
        self._base_color = self.definitions.get_format('RESET')
        self._active_patterns = []
        self._word_buffer = ""
        self._buffer_lock = asyncio.Lock()
        self._current_line_length = 0
        
        # Set up Rich console for rich text formatting
        self._setup_rich_console()

    def _setup_rich_console(self) -> None:
        """Initialize Rich console and styles."""
        self._rich_console = Console(
            force_terminal=True,
            color_system="truecolor",
            file=StringIO(),
            highlight=False
        )
        self.rich_style = {
            name: Style(color=cfg['rich'])
            for name, cfg in self.definitions.colors.items()
        }

    def get_visible_length(self, text: str) -> int:
        """
        Calculate the visible length of text, excluding ANSI codes and box chars.
        
        Args:
            text: Input text to measure
            
        Returns:
            Visible length of the text
        """
        # Strip ANSI escape sequences
        text = re.sub(r'\x1B\[[0-?]*[ -/]*[@-~]', '', text)
        # Remove box drawing characters
        for c in self.definitions.box_chars:
            text = text.replace(c, '')
        return len(text)

    def get_format(self, name: str) -> str:
        """Get format code by name."""
        return self.definitions.get_format(name)

    def get_base_color(self, color_name: str = 'GREEN') -> str:
        """
        Get the ANSI color code for a given color name.
        
        Args:
            color_name: Name of the color (defaults to 'GREEN')
            
        Returns:
            ANSI color code string
        """
        return self.definitions.get_color(color_name).get('ansi', '')
    
    def get_color(self, name: str) -> str:
        """Get ANSI color code by name."""
        return self.definitions.get_color(name).get('ansi', '')

    def get_rich_style(self, name: str) -> Style:
        """Get Rich style by name."""
        return self.rich_style.get(name, Style())

    def set_base_color(self, color: Optional[str] = None) -> None:
        """Set the base text color."""
        self._base_color = (self.get_color(color) if color 
                          else self.definitions.get_format('RESET'))

    async def write_styled(self, chunk: str) -> Tuple[str, str]:
        """
        Write styled text to the terminal.
        
        This method processes text chunks, applying active styles and managing
        word wrapping while maintaining proper terminal output.
        
        Args:
            chunk: Text chunk to style and write
            
        Returns:
            Tuple of (raw_text, styled_text)
        """
        if not chunk:
            return "", ""
        
        async with self._buffer_lock:
            return self._process_and_write(chunk)

    def _process_and_write(self, chunk: str) -> Tuple[str, str]:
        """
        Process and write text with proper styling.
        
        This internal method handles the actual text processing and writing,
        managing word wrapping and style application.
        """
        if not chunk:
            return "", ""
            
        self.terminal.hide_cursor()
        styled_out = ""
        
        try:
            # Handle box drawing characters differently
            if any(c in self.definitions.box_chars for c in chunk):
                self.terminal.write(chunk)
                return chunk, chunk
                
            # Process text normally
            for char in chunk:
                if char.isspace():
                    # Write buffered word if exists
                    if self._word_buffer:
                        word_length = self.get_visible_length(self._word_buffer)
                        
                        # Handle line wrapping
                        if self._current_line_length + word_length >= self.terminal.width:
                            self.terminal.write('\n')
                            styled_out += '\n'
                            self._current_line_length = 0
                            
                        # Write styled word
                        styled_word = self._style_chunk(self._word_buffer)
                        self.terminal.write(styled_word)
                        styled_out += styled_word
                        self._current_line_length += word_length
                        self._word_buffer = ""
                        
                    # Write the space character
                    self.terminal.write(char)
                    styled_out += char
                    if char == '\n':
                        self._current_line_length = 0
                    else:
                        self._current_line_length += 1
                else:
                    self._word_buffer += char
                    
            sys.stdout.flush()
            return chunk, styled_out
            
        finally:
            self.terminal.hide_cursor()

    def _style_chunk(self, text: str) -> str:
        """
        Apply active styles to a chunk of text.
        
        This method handles the actual style application, managing style
        patterns and their delimiters.
        
        Args:
            text: Text chunk to style
            
        Returns:
            Styled text with ANSI codes
        """
        if not text or any(c in self.definitions.box_chars for c in text):
            return text

        out = []
        
        # Reset styles if no patterns are active
        if not self._active_patterns:
            out.append(f"{self.definitions.get_format('ITALIC_OFF')}"
                      f"{self.definitions.get_format('BOLD_OFF')}"
                      f"{self._base_color}")

        # Process each character
        for i, char in enumerate(text):
            # Apply styles at word boundaries
            if i == 0 or text[i - 1].isspace():
                out.append(self._get_current_style())
                
            # Handle pattern endings
            active_pattern = (self.definitions.get_pattern(self._active_patterns[-1]) 
                            if self._active_patterns else None)
            if active_pattern and char == active_pattern.end:
                if not active_pattern.remove_delimiters:
                    out.append(self._get_current_style() + char)
                self._active_patterns.pop()
                out.append(self._get_current_style())
                continue
                
            # Handle pattern starts
            new_pattern = next((p for p in self.definitions.patterns.values() 
                              if p.start == char), None)
            if new_pattern:
                self._active_patterns.append(new_pattern.name)
                out.append(self._get_current_style())
                if not new_pattern.remove_delimiters:
                    out.append(char)
                continue
                
            out.append(char)
            
        return ''.join(out)

    def _get_current_style(self) -> str:
        """Get the combined style string for all active patterns."""
        style = [self._base_color]
        for name in self._active_patterns:
            pattern = self.definitions.get_pattern(name)
            if pattern and pattern.color:
                style[0] = self.definitions.get_color(pattern.color)['ansi']
            if pattern and pattern.style:
                style.extend(self.definitions.get_format(f'{s}_ON') 
                           for s in pattern.style)
        return ''.join(style)

    async def flush_styled(self) -> Tuple[str, str]:
        """
        Flush any remaining styled text and reset the styling state.
        
        Returns:
            Tuple of (raw_text, styled_text)
        """
        styled_out = ""
        try:
            # Write any remaining buffered word
            if self._word_buffer:
                word_length = self.get_visible_length(self._word_buffer)
                if self._current_line_length + word_length >= self.terminal.width:
                    self.terminal.write('\n')
                    styled_out += '\n'
                    self._current_line_length = 0
                styled_word = self._style_chunk(self._word_buffer)
                self.terminal.write(styled_word)
                styled_out += styled_word
                self._word_buffer = ""

            # Ensure proper line ending
            if not styled_out.endswith('\n'):
                self.terminal.write("\n")
                styled_out += "\n"
                
            # Reset styles
            self.terminal.write(self.definitions.get_format('RESET'))
            sys.stdout.flush()
            self._reset_output_state()
            
            return "", styled_out
            
        finally:
            self.terminal.hide_cursor()

    def _reset_output_state(self) -> None:
        """Reset all internal styling state."""
        self._active_patterns.clear()
        self._word_buffer = ""
        self._current_line_length = 0

    def append_single_blank_line(self, text: str) -> str:
        """
        Ensure text ends with exactly one blank line.
        
        Args:
            text: Input text
            
        Returns:
            Text with exactly one blank line at the end
        """
        return text.rstrip('\n') + "\n\n" if text.strip() else text

    def set_output_color(self, color: Optional[str] = None) -> None:
        """
        Set the output text color (alias for set_base_color for backward compatibility).
        
        Args:
            color: Color name to set, or None for reset
        """
        self.set_base_color(color)

    def set_base_color(self, color: Optional[str] = None) -> None:
        """
        Set the base text color.
        
        Args:
            color: Color name to set, or None for reset
        """
        self._base_color = (self.get_color(color) if color 
                          else self.definitions.get_format('RESET'))
