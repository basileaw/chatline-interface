import sys
import shutil
import re
from typing import List, Optional

# ANSI handling
ANSI_REGEX = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')

class RealUtilities:
    def get_visible_length(self, text: str) -> int:
        """Get visible length of text, ignoring ANSI escape codes."""
        return len(ANSI_REGEX.sub('', text))

    def get_terminal_width(self) -> int:
        """Get current terminal width."""
        return shutil.get_terminal_size().columns

    def show_cursor(self) -> None:
        """Show the terminal cursor."""
        if sys.stdout.isatty():
            sys.stdout.write("\033[?25h")
            sys.stdout.flush()

    def hide_cursor(self) -> None:
        """Hide the terminal cursor."""
        if sys.stdout.isatty():
            sys.stdout.write("\033[?25l")
            sys.stdout.flush()

    def clear_screen(self) -> None:
        """Clear the terminal screen and reset cursor position."""
        if sys.stdout.isatty():
            sys.stdout.write("\033[2J\033[H")
            sys.stdout.flush()

    def write_and_flush(self, text: str) -> None:
        """Write text to stdout and flush buffer."""
        sys.stdout.write(text)
        sys.stdout.flush()

    # Helper methods that might be useful for implementations
    def split_into_display_lines(self, text: str, width: Optional[int] = None) -> List[str]:
        """Split text into lines that fit within terminal width."""
        if width is None:
            width = self.get_terminal_width()
            
        display_lines = []
        words = text.split()
        current_line = []
        current_length = 0
        
        for word in words:
            word_length = len(word) + (1 if current_length > 0 else 0)
            if current_length + word_length <= width:
                current_line.append(word)
                current_length += word_length
            else:
                if current_line:
                    display_lines.append(' '.join(current_line))
                current_line = [word]
                current_length = len(word)
        
        if current_line:
            display_lines.append(' '.join(current_line))
        return display_lines

    def handle_long_word(self, word: str, width: Optional[int] = None) -> List[str]:
        """Split a word that exceeds terminal width into chunks."""
        if width is None:
            width = self.get_terminal_width()
            
        chunks = []
        while word:
            if len(word) <= width:
                chunks.append(word)
                break
            chunks.append(word[:width])
            word = word[width:]
        return chunks

# Legacy function wrappers for backward compatibility
def get_visible_length(text: str) -> int:
    return RealUtilities().get_visible_length(text)

def get_terminal_width() -> int:
    return RealUtilities().get_terminal_width()

def show_cursor() -> None:
    RealUtilities().show_cursor()

def hide_cursor() -> None:
    RealUtilities().hide_cursor()

def manage_cursor(show: bool) -> None:
    if show:
        RealUtilities().show_cursor()
    else:
        RealUtilities().hide_cursor()

def clear_screen() -> None:
    RealUtilities().clear_screen()

def write_and_flush(text: str) -> None:
    RealUtilities().write_and_flush(text)

def split_into_display_lines(text: str, width: Optional[int] = None) -> List[str]:
    return RealUtilities().split_into_display_lines(text, width)

def handle_long_word(word: str, width: Optional[int] = None) -> List[str]:
    return RealUtilities().handle_long_word(word, width)