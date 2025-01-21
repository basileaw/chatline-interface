# scrolling_input.py
import sys
import time
from typing import List, Tuple, Optional

class ScrollingInput:
    """Handles input with scrolling animation effect."""
    
    def __init__(self, demo_content: List[str], check_tty: bool = True):
        """
        Initialize ScrollingInput with demo content.
        
        Args:
            demo_content: Content to display below user input
            check_tty: If True, will check if stdout is a terminal before operations
        """
        self.demo_content = demo_content
        self.check_tty = check_tty
        
    def _should_execute(self) -> bool:
        """Determine if terminal operations should execute."""
        return not self.check_tty or sys.stdout.isatty()
    
    def clear_screen(self) -> None:
        """Clear the terminal screen."""
        if self._should_execute():
            sys.stdout.write('\033[2J\033[H')
            sys.stdout.flush()
            
    def toggle_cursor(self, show: bool = True) -> None:
        """Show or hide the terminal cursor."""
        if self._should_execute():
            sys.stdout.write('\033[?25h' if show else '\033[?25l')
            sys.stdout.flush()
            
    def display_frame(self, content: str, delay: float = 0.1) -> None:
        """Display a single frame of content with optional delay."""
        if self._should_execute():
            self.clear_screen()
            sys.stdout.write(content)
            sys.stdout.flush()
            if delay > 0:
                time.sleep(delay)
    
    def get_input(self, 
                  prompt: str = "> ",
                  content_lines: Optional[List[str]] = None
                  ) -> Tuple[str, Optional[List[str]]]:
        """
        Get user input with scrolling effect. Previous input stays at top while content scrolls.
        
        Args:
            prompt: Input prompt to display
            content_lines: Optional previous content to display and scroll
            
        Returns:
            Tuple of (user_input, new_content_lines)
        """
        try:
            # Display initial content if any
            if content_lines and self._should_execute():
                self.clear_screen()
                print("\n".join(content_lines) + "\n")
            
            # Get user input
            self.toggle_cursor(True)
            user_input = input(prompt)
            self.toggle_cursor(False)
            
            # Handle scrolling animation if needed
            if content_lines and self._should_execute():
                input_line = f"{prompt}{user_input}"
                
                # Scroll up animation
                for i in range(len(content_lines) + 1):
                    remaining = content_lines[i:] if i < len(content_lines) else []
                    content = "\n".join(remaining) + "\n\n" + input_line if remaining else input_line
                    self.display_frame(content)
                
                # Pause briefly on input
                self.display_frame(input_line)
                time.sleep(0.5)
                
                # Show final state
                new_content = [input_line, ""] + self.demo_content
                self.display_frame("\n".join(new_content) + "\n")
                return user_input, new_content
                
            return user_input, content_lines
            
        finally:
            self.toggle_cursor(True)

def run_demo():
    """Demo of scrolling input functionality."""
    demo_lines = [
        "This is a demonstration of scrolling input.",
        "When you type and submit a message, all content",
        "will scroll up and out of view. Your message will",
        "then appear at the top with this content below it."
    ]
    
    last_message = None
    scroller = ScrollingInput(demo_lines)
    
    while True:
        current_content = [last_message, ""] + demo_lines if last_message else demo_lines
        result, _ = scroller.get_input(content_lines=current_content)
        
        if result.lower() == 'exit':
            break
            
        last_message = f"> {result}"

if __name__ == "__main__":
    run_demo()