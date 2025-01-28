# reverse_stream.py

import asyncio
from dataclasses import dataclass
from typing import List

@dataclass
class StyledWord:
    raw_text: str
    styled_text: str
    active_patterns: List[str]

class ReverseStreamer:
    """Handles reverse streaming of text with styling and animations."""
    
    def __init__(self, utilities, base_color='GREEN'):
        self.utils = utilities
        self._base_color = self.utils.get_base_color(base_color)
        
        # Get pattern maps from utilities
        self.by_name = self.utils.by_name
        self.start_map = self.utils.start_map
        self.end_map = self.utils.end_map

    def split_into_styled_words(self, text: str) -> List[StyledWord]:
        """Split text into styled words while preserving formatting."""
        words = []
        current = {'word': [], 'styled': [], 'patterns': []}
        i = 0
        
        while i < len(text):
            char = text[i]
            
            if char in self.start_map:
                pattern = self.start_map[char]
                current['patterns'].append(pattern.name)
                if not pattern.remove_delimiters:
                    current['word'].append(char)
                    current['styled'].append(char)
            elif current['patterns'] and char in self.end_map:
                pattern = self.by_name[current['patterns'][-1]]
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
        current_style = self.utils.get_format('RESET') + self._base_color
        
        for line in lines:
            line_content = [current_style]
            for word in line:
                new_style = self.utils.get_style(word.active_patterns, self._base_color)
                if new_style != current_style:
                    line_content.append(new_style)
                    current_style = new_style
                line_content.append(word.styled_text + " ")
                
            formatted_line = "".join(line_content).rstrip()
            if formatted_line:
                formatted_lines.append(formatted_line)
                
        result = "\n".join(formatted_lines)
        if current_style != self.utils.get_format('RESET') + self._base_color:
            result += self.utils.get_format('RESET') + self._base_color
            
        return result

    async def update_screen(self, content: str = "", preserved_msg: str = "", no_spacing: bool = False):
        """Update the terminal screen with formatted content."""
        self.utils.clear_screen()
        
        if content:
            if preserved_msg:
                spacing = "" if no_spacing else "\n\n"
                self.utils.write_and_flush(preserved_msg + spacing)
            self.utils.write_and_flush(content)
        else:
            self.utils.write_and_flush(preserved_msg)
            
        self.utils.write_and_flush(self.utils.get_format('RESET'))
        await asyncio.sleep(0.01)

    async def reverse_stream(self, styled_text: str, preserved_msg: str = "", delay: float = 0.08):
        """Animate the reverse streaming of styled text."""
        lines = [self.split_into_styled_words(line) for line in styled_text.splitlines()]
        no_spacing = not bool(preserved_msg)
        
        for line_idx in range(len(lines) - 1, -1, -1):
            while lines[line_idx]:
                lines[line_idx].pop()
                formatted = self.format_lines(lines)
                await self.update_screen(formatted, preserved_msg, no_spacing)
                await asyncio.sleep(delay)
                
        if preserved_msg:
            await self.reverse_stream_dots(preserved_msg)
            
        await self.update_screen()  # Clear screen for input

    async def reverse_stream_dots(self, preserved_msg: str) -> str:
        """Animate the removal of dots from the preserved message."""
        msg_without_dots = preserved_msg.rstrip('.')
        num_dots = len(preserved_msg) - len(msg_without_dots)
        
        for i in range(num_dots - 1, -1, -1):
            await self.update_screen("", msg_without_dots + '.' * i)
            await asyncio.sleep(0.08)
            
        return msg_without_dots