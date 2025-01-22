# scrolling_input.py
import sys
import time
from typing import List, Tuple, Optional

def clear_screen(): sys.stdout.write('\033[2J\033[H'); sys.stdout.flush()
def toggle_cursor(show=True): sys.stdout.write('\033[?25h' if show else '\033[?25l'); sys.stdout.flush()
def display_frame(content, delay=0.1): clear_screen(); sys.stdout.write(content); sys.stdout.flush(); time.sleep(delay)

def scrolling_input(prompt="> ", content_lines=None):
    """
    Input with scrolling effect. Previous input stays at top while content scrolls.
    Returns: tuple (user_input, new_content_lines)
    """
    try:
        if content_lines and sys.stdout.isatty():
            print("\n".join(content_lines) + "\n")
        
        toggle_cursor(True)
        user_input = input(prompt)
        toggle_cursor(False)
        
        if content_lines and sys.stdout.isatty():
            input_line = f"{prompt}{user_input}"
            
            # Scroll up
            for i in range(len(content_lines) + 1):
                remaining = content_lines[i:] if i < len(content_lines) else []
                content = "\n".join(remaining) + "\n\n" + input_line if remaining else input_line
                display_frame(content)
            
            # Final position at top
            display_frame(input_line)
            return user_input, [input_line]
            
        return user_input, content_lines
        
    finally:
        toggle_cursor(True)