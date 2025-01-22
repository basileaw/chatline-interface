import sys
import time
from dataclasses import dataclass
from typing import List, Tuple
from output_handler import OutputHandler, FORMATS

@dataclass
class StyledWord:
    """Represents a word with its associated styling information"""
    raw_text: str
    styled_text: str
    active_patterns: List[str]

class ReverseStreamer:
    """Handles reverse streaming of styled text"""
    
    def __init__(self, output_handler: OutputHandler, delay: float = 0.08):
        self.output_handler = output_handler
        self.delay = delay
    
    def split_into_styled_words(self, text: str) -> List[StyledWord]:
        """Split text into words while preserving styling"""
        words = []
        current_word = []
        current_styled = []
        active_patterns = []
        
        i = 0
        while i < len(text):
            # Check for pattern starts
            if text[i] in self.output_handler.start_map:
                pattern = self.output_handler.start_map[text[i]]
                active_patterns.append(pattern.name)
                if not pattern.remove_delimiters:
                    current_word.append(text[i])
                    current_styled.append(text[i])
                i += 1
                continue
            
            # Check for pattern ends
            if active_patterns and text[i] in self.output_handler.end_map:
                pattern = self.output_handler.by_name[active_patterns[-1]]
                if text[i] == pattern.end:
                    if not pattern.remove_delimiters:
                        current_word.append(text[i])
                        current_styled.append(text[i])
                    active_patterns.pop()
                    i += 1
                    continue
            
            # Handle whitespace - break into words
            if text[i].isspace():
                if current_word:
                    words.append(StyledWord(
                        raw_text=''.join(current_word),
                        styled_text=''.join(current_styled),
                        active_patterns=active_patterns.copy()
                    ))
                    current_word = []
                    current_styled = []
                i += 1
                continue
                
            # Add character to current word
            current_word.append(text[i])
            current_styled.append(text[i])
            i += 1
        
        # Add final word if exists
        if current_word:
            words.append(StyledWord(
                raw_text=''.join(current_word),
                styled_text=''.join(current_styled),
                active_patterns=active_patterns.copy()
            ))
            
        return words

    def clear_screen(self):
        """Clear the terminal screen"""
        if sys.stdout.isatty():
            sys.stdout.write("\033[2J\033[H")
            sys.stdout.flush()

    def redraw_screen(self, lines: List[List[StyledWord]], preserved_msg: str):
        """Redraw the screen with current state"""
        self.clear_screen()
        
        # Write preserved message with no formatting
        sys.stdout.write(FORMATS['RESET'])
        sys.stdout.write(preserved_msg + "\n\n")
        
        # Track current style state
        current_style = FORMATS['RESET'] + self.output_handler.base_color
        
        # Write remaining lines
        for line in lines:
            line_style = FORMATS['RESET'] + self.output_handler.base_color
            for word in line:
                new_style = self.get_style(word.active_patterns)
                if new_style != current_style:
                    sys.stdout.write(new_style)
                    current_style = new_style
                sys.stdout.write(word.styled_text)
                sys.stdout.write(" ")
            sys.stdout.write("\n")
            if line_style != current_style:
                sys.stdout.write(line_style)
                current_style = line_style
        
        sys.stdout.write(FORMATS['RESET'])
        sys.stdout.flush()
    
    def get_style(self, active_patterns: List[str]) -> str:
        """Get ANSI style string for current pattern state"""
        color = self.output_handler.base_color
        italic = False
        for name in active_patterns:
            pattern = self.output_handler.by_name[name]
            if pattern.color:
                color = pattern.color
            if pattern.italic:
                italic = True
        return (FORMATS['ITALIC_ON'] if italic else FORMATS['ITALIC_OFF']) + color
    
    async def reverse_stream(self, styled_text: str, preserved_msg: str) -> None:
        """Perform reverse streaming animation"""
        # Split into lines and words
        lines = [self.split_into_styled_words(line) for line in styled_text.splitlines()]
        
        # Process lines from bottom to top (excluding preserved message)
        for line_idx in range(len(lines) - 1, -1, -1):
            # Remove words from right to left
            while lines[line_idx]:
                lines[line_idx].pop()  # Remove last word
                self.redraw_screen(lines, preserved_msg)
                time.sleep(self.delay)
        
        # Now remove dots one by one if they exist
        msg_without_dots = preserved_msg.rstrip('.')
        num_dots = len(preserved_msg) - len(msg_without_dots)
        
        if num_dots > 0:
            for i in range(num_dots - 1, -1, -1):
                self.clear_screen()
                sys.stdout.write(msg_without_dots + '.' * i)
                sys.stdout.write(FORMATS['RESET'])
                sys.stdout.flush()
                time.sleep(self.delay)
        
        # Just clear the screen and don't write anything
        self.clear_screen()
        sys.stdout.write(FORMATS['RESET'])
        sys.stdout.flush()