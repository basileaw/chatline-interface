# reverse_stream.py

import asyncio
from dataclasses import dataclass
from typing import List, Optional
from painter import FORMATS
from utilities import (
    clear_screen,
    write_and_flush
)

@dataclass
class StyledWord:
    raw_text: str
    styled_text: str
    active_patterns: List[str]

class ReverseStreamer:
    """Handles reverse streaming of text with styling and animations."""
    
    def __init__(self, text_painter, delay: float = 0.08):
        if not text_painter:
            raise ValueError("TextPainter must be provided")
        self.painter = text_painter
        self.delay = delay
        
    def get_style(self, active_patterns: List[str]) -> str:
        """Get the combined ANSI style string for a set of active patterns."""
        color = self.painter.base_color
        italic = False
        bold = False
        
        for name in active_patterns:
            pattern = self.painter.by_name[name]
            if pattern.color:
                color = pattern.color
            if pattern.italic:
                italic = True
            if pattern.bold:
                bold = True
                
        style = color
        if italic: style += FORMATS['ITALIC_ON']
        if bold: style += FORMATS['BOLD_ON']
        return style

    def split_into_styled_words(self, text: str) -> List[StyledWord]:
        """Split text into styled words while preserving formatting."""
        words = []
        current = {'word': [], 'styled': [], 'patterns': []}
        
        i = 0
        while i < len(text):
            char = text[i]
            
            if char in self.painter.start_map:
                pattern = self.painter.start_map[char]
                current['patterns'].append(pattern.name)
                if not pattern.remove_delimiters:
                    current['word'].append(char)
                    current['styled'].append(char)
                    
            elif current['patterns'] and char in self.painter.end_map:
                pattern = self.painter.by_name[current['patterns'][-1]]
                if char == pattern.end:
                    if not pattern.remove_delimiters:
                        current['word'].append(char)
                        current['styled'].append(char)
                    current['patterns'].pop()
                    
            elif char.isspace():
                if current['word']:
                    words.append(StyledWord(
                        raw_text=''.join(current['word']),
                        styled_text=''.join(current['styled']),
                        active_patterns=current['patterns'].copy()
                    ))
                    current = {'word': [], 'styled': [], 'patterns': []}
                    
            else:
                current['word'].append(char)
                current['styled'].append(char)
                
            i += 1
            
        if current['word']:
            words.append(StyledWord(
                raw_text=''.join(current['word']),
                styled_text=''.join(current['styled']),
                active_patterns=current['patterns'].copy()
            ))
            
        return words

    def format_lines(self, lines: List[List[StyledWord]]) -> str:
        """Format lines of styled words into a complete styled string."""
        formatted_lines = []
        current_style = FORMATS['RESET'] + self.painter.base_color
        
        for line in lines:
            line_content = [current_style]
            for word in line:
                new_style = self.get_style(word.active_patterns)
                if new_style != current_style:
                    line_content.append(new_style)
                    current_style = new_style
                line_content.append(word.styled_text + " ")
                
            formatted_line = "".join(line_content).rstrip()
            if formatted_line:
                formatted_lines.append(formatted_line)
        
        result = "\n".join(formatted_lines)
        if current_style != FORMATS['RESET'] + self.painter.base_color:
            result += FORMATS['RESET'] + self.painter.base_color
            
        return result

    async def update_screen(self, content: str = "", preserved_msg: str = "", no_spacing: bool = False):
        """Update the terminal screen with formatted content."""
        clear_screen()
        
        if content:
            if preserved_msg:
                spacing = "" if no_spacing else "\n\n"
                write_and_flush(preserved_msg + spacing)
            write_and_flush(content)
        else:
            write_and_flush(preserved_msg)
            
        write_and_flush(FORMATS['RESET'])
        # Brief pause to ensure smooth animation
        await asyncio.sleep(0.01)

    async def reverse_stream_dots(self, preserved_msg: str) -> str:
        """Animate the removal of dots from the preserved message."""
        msg_without_dots = preserved_msg.rstrip('.')
        num_dots = len(preserved_msg) - len(msg_without_dots)
        
        for i in range(num_dots - 1, -1, -1):
            await self.update_screen("", msg_without_dots + '.' * i)
            await asyncio.sleep(self.delay)
            
        return msg_without_dots

    async def reverse_stream(self, styled_text: str, preserved_msg: str) -> None:
        """Animate the reverse streaming of styled text."""
        lines = [self.split_into_styled_words(line) for line in styled_text.splitlines()]
        no_spacing = not bool(preserved_msg)
        
        for line_idx in range(len(lines) - 1, -1, -1):
            while lines[line_idx]:
                lines[line_idx].pop()
                formatted = self.format_lines(lines)
                await self.update_screen(formatted, preserved_msg, no_spacing)
                await asyncio.sleep(self.delay)
        
        if preserved_msg:
            await self.reverse_stream_dots(preserved_msg)
            
        await self.update_screen()  # Clear screen for input