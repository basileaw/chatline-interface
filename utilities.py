# utilities.py

import sys
import shutil
import re
from typing import List, Optional

# ANSI handling
ANSI_REGEX = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')

def get_visible_length(text: str) -> int:
    """
    Get visible length of text, ignoring ANSI escape codes.
    
    Args:
        text: Text to measure
        
    Returns:
        int: Visible length of text
    """
    return len(ANSI_REGEX.sub('', text))

def get_terminal_width() -> int:
    """Get current terminal width."""
    return shutil.get_terminal_size().columns

# Cursor management
def show_cursor() -> None:
    """Show the terminal cursor."""
    if sys.stdout.isatty():
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()

def hide_cursor() -> None:
    """Hide the terminal cursor."""
    if sys.stdout.isatty():
        sys.stdout.write("\033[?25l")
        sys.stdout.flush()

def manage_cursor(show: bool) -> None:
    """
    Show or hide the terminal cursor.
    
    Args:
        show: True to show cursor, False to hide
    """
    if show:
        show_cursor()
    else:
        hide_cursor()

# Screen management
def clear_screen() -> None:
    """Clear the terminal screen and reset cursor position."""
    if sys.stdout.isatty():
        sys.stdout.write("\033[2J\033[H")
        sys.stdout.flush()

# Text wrapping
def split_into_display_lines(text: str, width: Optional[int] = None) -> List[str]:
    """
    Split text into lines that fit within terminal width.
    
    Args:
        text: Text to split
        width: Maximum line width (defaults to terminal width)
        
    Returns:
        List[str]: Lines of text
    """
    if width is None:
        width = get_terminal_width()
        
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

def handle_long_word(word: str, width: Optional[int] = None) -> List[str]:
    """
    Split a word that exceeds terminal width into chunks.
    
    Args:
        word: Word to split
        width: Maximum chunk width (defaults to terminal width)
        
    Returns:
        List[str]: Word chunks
    """
    if width is None:
        width = get_terminal_width()
        
    chunks = []
    while word:
        if len(word) <= width:
            chunks.append(word)
            break
        chunks.append(word[:width])
        word = word[width:]
    return chunks

# Output helpers
def write_and_flush(text: str) -> None:
    """
    Write text to stdout and flush buffer.
    
    Args:
        text: Text to write
    """
    sys.stdout.write(text)
    sys.stdout.flush()