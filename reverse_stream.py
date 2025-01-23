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

    def perform_screen_update(self, content: str, preserved_msg: str, no_spacing: bool = False):
        """Wrapper for all screen updates."""
        self.clear_screen()
        sys.stdout.write(FORMATS['RESET'])
        
        if content:
            if preserved_msg:
                # Only add double newlines if we're not in no_spacing mode
                spacing = "" if no_spacing else "\n\n"
                sys.stdout.write(preserved_msg + spacing)
            sys.stdout.write(content)
        else:
            sys.stdout.write(preserved_msg)
            
        sys.stdout.write(FORMATS['RESET'])
        sys.stdout.flush()

    def format_lines(self, lines: List[List[StyledWord]]) -> str:
        """Format lines into a single string with proper styling"""
        formatted_lines = []
        current_style = FORMATS['RESET'] + self.output_handler.base_color
        
        for line in lines:
            line_content = []
            # Add initial style for the line
            if current_style:
                line_content.append(current_style)
                
            # Process each word in the line
            for word in line:
                new_style = self.get_style(word.active_patterns)
                if new_style != current_style:
                    line_content.append(new_style)
                    current_style = new_style
                line_content.append(word.styled_text)
                line_content.append(" ")
                
            # Create the full line with styles inline
            formatted_line = "".join(line_content).rstrip()
            if formatted_line:  # Only add non-empty lines
                formatted_lines.append(formatted_line)
        
        # Join only the actual content lines
        result = "\n".join(formatted_lines)
        # Ensure style is reset at the end if needed
        if current_style != FORMATS['RESET'] + self.output_handler.base_color:
            result += FORMATS['RESET'] + self.output_handler.base_color
            
        return result

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

    async def reverse_stream_dots(self, preserved_msg: str) -> str:
        """Handle the dot removal animation. Returns the final message without dots."""
        msg_without_dots = preserved_msg.rstrip('.')
        num_dots = len(preserved_msg) - len(msg_without_dots)
        
        if num_dots > 0:
            for i in range(num_dots - 1, -1, -1):
                content = msg_without_dots + '.' * i
                self.perform_screen_update("", content)
                time.sleep(self.delay)
        
        return msg_without_dots
    
    def prepare_for_input(self):
        """Prepare the terminal for user input after streaming"""
        self.clear_screen()
        sys.stdout.write(FORMATS['RESET'])
        sys.stdout.flush()
    
    async def reverse_stream(self, styled_text: str, preserved_msg: str) -> None:
        # Split into lines and words
        lines = [self.split_into_styled_words(line) for line in styled_text.splitlines()]
        
        # Use no_spacing if there's no preserved message (silent retry)
        no_spacing = not bool(preserved_msg)
        
        for line_idx in range(len(lines) - 1, -1, -1):
            while lines[line_idx]:
                lines[line_idx].pop()
                formatted_content = self.format_lines(lines)
                self.perform_screen_update(formatted_content, preserved_msg, no_spacing=no_spacing)
                time.sleep(self.delay)
        
        # Handle dot animation separately and get final message
        if preserved_msg:
            await self.reverse_stream_dots(preserved_msg)
        
        # Prepare for next input
        self.prepare_for_input()