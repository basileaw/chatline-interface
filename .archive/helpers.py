# helpers.py
import sys
import time

def clear_screen():
    """Clear the terminal screen."""
    if sys.stdout.isatty():
        sys.stdout.write("\033[2J\033[H")
        sys.stdout.flush()

def hide_cursor():
    """Hide the terminal cursor."""
    if sys.stdout.isatty():
        sys.stdout.write("\033[?25l")
        sys.stdout.flush()

def show_cursor():
    """Show the terminal cursor."""
    if sys.stdout.isatty():
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()

def scroll_text(lines, prompt, delay=0.1):
    """Scroll text upward with a given delay."""
    for i in range(len(lines)+1):
        clear_screen()
        for ln in lines[i:]:
            print(ln)
        if i < len(lines):
            print()
        print(prompt, end="", flush=True)
        time.sleep(delay)

