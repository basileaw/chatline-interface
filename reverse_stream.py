# reverse_stream.py

import sys
import time
from dataclasses import dataclass
from typing import List
from output_handler import OutputHandler, FORMATS

@dataclass
class StyledWord:
    raw_text: str
    styled_text: str
    active_patterns: List[str]

class ReverseStreamer:
    def __init__(self, output_handler: OutputHandler, delay: float = 0.08):
        self.output_handler = output_handler
        self.delay = delay
    
    def get_style(self, active_patterns: List[str]) -> str:
        color = self.output_handler.base_color
        italic = False
        for name in active_patterns:
            pattern = self.output_handler.by_name[name]
            if pattern.color:
                color = pattern.color
            if pattern.italic:
                italic = True
        return (FORMATS['ITALIC_ON'] if italic else FORMATS['ITALIC_OFF']) + color

    def split_into_styled_words(self, text: str) -> List[StyledWord]:
        words = []
        current = {'word': [], 'styled': [], 'patterns': []}
        
        i = 0
        while i < len(text):
            char = text[i]
            
            if char in self.output_handler.start_map:
                pattern = self.output_handler.start_map[char]
                current['patterns'].append(pattern.name)
                if not pattern.remove_delimiters:
                    current['word'].append(char)
                    current['styled'].append(char)
                    
            elif current['patterns'] and char in self.output_handler.end_map:
                pattern = self.output_handler.by_name[current['patterns'][-1]]
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
        formatted_lines = []
        current_style = FORMATS['RESET'] + self.output_handler.base_color
        
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
        if current_style != FORMATS['RESET'] + self.output_handler.base_color:
            result += FORMATS['RESET'] + self.output_handler.base_color
            
        return result

    def update_screen(self, content: str = "", preserved_msg: str = "", no_spacing: bool = False):
        if sys.stdout.isatty():
            sys.stdout.write("\033[2J\033[H")  # Clear screen and reset cursor
            sys.stdout.write(FORMATS['RESET'])
            
            if content:
                if preserved_msg:
                    spacing = "" if no_spacing else "\n\n"
                    sys.stdout.write(preserved_msg + spacing)
                sys.stdout.write(content)
            else:
                sys.stdout.write(preserved_msg)
                
            sys.stdout.write(FORMATS['RESET'])
            sys.stdout.flush()

    async def reverse_stream_dots(self, preserved_msg: str) -> str:
        msg_without_dots = preserved_msg.rstrip('.')
        num_dots = len(preserved_msg) - len(msg_without_dots)
        
        for i in range(num_dots - 1, -1, -1):
            self.update_screen("", msg_without_dots + '.' * i)
            time.sleep(self.delay)
            
        return msg_without_dots

    async def reverse_stream(self, styled_text: str, preserved_msg: str) -> None:
        lines = [self.split_into_styled_words(line) for line in styled_text.splitlines()]
        no_spacing = not bool(preserved_msg)
        
        for line_idx in range(len(lines) - 1, -1, -1):
            while lines[line_idx]:
                lines[line_idx].pop()
                formatted = self.format_lines(lines)
                self.update_screen(formatted, preserved_msg, no_spacing)
                time.sleep(self.delay)
        
        if preserved_msg:
            await self.reverse_stream_dots(preserved_msg)
            
        self.update_screen()  # Clear screen for input