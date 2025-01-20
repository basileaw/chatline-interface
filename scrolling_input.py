import os, sys, time

def clear_screen(): sys.stdout.write('\033[2J\033[H'); sys.stdout.flush()
def toggle_cursor(show=True): sys.stdout.write('\033[?25h' if show else '\033[?25l'); sys.stdout.flush()
def display_frame(content, delay=0.1): clear_screen(); sys.stdout.write(content); sys.stdout.flush(); time.sleep(delay)

def scrolling_input(prompt="> ", content_lines=None):
    """
    Input with scrolling effect. Previous input stays at top while content scrolls.
    Returns: tuple (user_input, new_content_lines)
    
    Usage:
        current_content = [last_message, ""] + demo_lines if last_message else demo_lines
        result, _ = scrolling_input(content_lines=current_content)
        last_message = f"> {result}"
    """
    try:
        if content_lines and sys.stdout.isatty():
            clear_screen()
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
            
            # Pause on input
            display_frame(input_line)
            time.sleep(0.5)
            
            # Final state
            new_content = [input_line, ""] + demo_lines
            display_frame("\n".join(new_content) + "\n")
            return user_input, new_content
            
        return user_input, content_lines
    finally:
        toggle_cursor(True)

if __name__ == "__main__":
    demo_lines = [
        "This is a demonstration of scrolling input.",
        "When you type and submit a message, all content",
        "will scroll up and out of view. Your message will",
        "then appear at the top with this content below it."
    ]
    
    last_message = None
    while True:
        result, _ = scrolling_input(
            content_lines=[last_message, ""] + demo_lines if last_message else demo_lines
        )
        if result.lower() == 'exit': break
        last_message = f"> {result}"