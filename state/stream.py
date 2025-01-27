# stream.py

import sys
import asyncio
from typing import List, Optional, Tuple

class TextProcessor:
    """Handles text styling, wrapping, and terminal output."""
    
    def __init__(self, utilities, base_color='GREEN'):
        self.utils = utilities
        self._base_color = self.utils.get_base_color(base_color)
        self.active_patterns: List[str] = []
        self._buffer_lock = asyncio.Lock()
        
        # Get pattern maps from utilities
        self.by_name = self.utils.by_name
        self.start_map = self.utils.start_map
        self.end_map = self.utils.end_map
        
        # Output handler state
        self.current_line_length = 0
        self.word_buffer = ""

    def _process_chunk(self, text: str) -> str:
        """Process a chunk of text and apply ANSI styling."""
        if not text:
            return ""
            
        out, i = [], 0
        
        if not self.active_patterns:
            out.append(self.utils.get_format('ITALIC_OFF') + 
                      self.utils.get_format('BOLD_OFF') + 
                      self._base_color)
            
        while i < len(text):
            ch = text[i]
            
            if i == 0 or text[i-1].isspace():
                out.append(self.utils.get_style(self.active_patterns, self._base_color))
                
            if self.active_patterns and ch in self.end_map:
                if ch == self.by_name[self.active_patterns[-1]].end:
                    pat = self.by_name[self.active_patterns[-1]]
                    if not pat.remove_delimiters:
                        out.append(self.utils.get_style(self.active_patterns, self._base_color) + ch)
                    self.active_patterns.pop()
                    out.append(self.utils.get_style(self.active_patterns, self._base_color))
                    i += 1
                    continue
                    
            if ch in self.start_map:
                new_pat = self.start_map[ch]
                self.active_patterns.append(new_pat.name)
                out.append(self.utils.get_style(self.active_patterns, self._base_color))
                if not new_pat.remove_delimiters:
                    out.append(ch)
                i += 1
                continue
                
            out.append(ch)
            i += 1
            
        return "".join(out)

    def process_and_write(self, chunk: str) -> Tuple[str, str]:
        """Process and write a chunk of text with proper wrapping."""
        if not chunk:
            return ("", "")

        width = self.utils.get_terminal_width()
        raw_out, styled_out = chunk, ""

        i = 0
        while i < len(chunk):
            char = chunk[i]

            if char.isspace():
                if self.word_buffer:
                    word_length = self.utils.get_visible_length(self.word_buffer)
                    
                    if word_length > width:
                        word_chunks = self.utils.handle_long_word(self.word_buffer, width)
                        for idx, word_chunk in enumerate(word_chunks):
                            if idx > 0:
                                self.utils.write_and_flush("\n")
                                styled_out += "\n"
                                self.current_line_length = 0
                            
                            styled_chunk = self._process_chunk(word_chunk)
                            self.utils.write_and_flush(styled_chunk)
                            styled_out += styled_chunk
                            self.current_line_length = len(word_chunk)
                    else:
                        if self.current_line_length + word_length > width:
                            self.utils.write_and_flush("\n")
                            styled_out += "\n"
                            self.current_line_length = 0
                        
                        styled_word = self._process_chunk(self.word_buffer)
                        self.utils.write_and_flush(styled_word)
                        styled_out += styled_word
                        self.current_line_length += word_length
                    
                    self.word_buffer = ""

                if char == '\n':
                    self.utils.write_and_flush("\n")
                    styled_out += "\n"
                    self.current_line_length = 0
                elif self.current_line_length + 1 <= width:
                    self.utils.write_and_flush(char)
                    styled_out += char
                    self.current_line_length += 1
            else:
                self.word_buffer += char

            i += 1

        sys.stdout.flush()
        return (raw_out, styled_out)

    async def add(self, chunk: str, output_handler=None) -> Tuple[str, str]:
        """Process a chunk of text immediately."""
        if not chunk:
            return "", ""
            
        async with self._buffer_lock:
            return self.process_and_write(chunk)

    async def flush(self, output_handler=None) -> Tuple[str, str]:
        """Flush any remaining buffered content."""
        styled_out = ""
        
        if self.word_buffer:
            width = self.utils.get_terminal_width()
            word_length = self.utils.get_visible_length(self.word_buffer)
            
            if word_length > width:
                word_chunks = self.utils.handle_long_word(self.word_buffer, width)
                for idx, chunk in enumerate(word_chunks):
                    if idx > 0:
                        self.utils.write_and_flush("\n")
                        styled_out += "\n"
                    styled_chunk = self._process_chunk(chunk)
                    self.utils.write_and_flush(styled_chunk)
                    styled_out += styled_chunk
            else:
                if self.current_line_length + word_length > width:
                    self.utils.write_and_flush("\n")
                    styled_out += "\n"
                styled_word = self._process_chunk(self.word_buffer)
                self.utils.write_and_flush(styled_word)
                styled_out += styled_word
            
            self.word_buffer = ""

        if self.current_line_length > 0:
            self.utils.write_and_flush("\n")
            styled_out += "\n"

        self.utils.write_and_flush(self.utils.get_format('RESET'))
        sys.stdout.flush()
        self.reset()
        self.current_line_length = 0

        return "", styled_out

    def reset(self) -> None:
        """Reset all active patterns and buffers."""
        self.active_patterns.clear()
        self.word_buffer = ""
        self.current_line_length = 0

class RawOutputHandler:
    """Simple pass-through handler for raw output."""
    def __init__(self, utilities):
        self.utils = utilities
        self._buffer_lock = asyncio.Lock()
        
    def process_and_write(self, chunk: str) -> Tuple[str, str]:
        self.utils.write_and_flush(chunk)
        return (chunk, chunk)
        
    def flush(self): pass

    async def add(self, chunk: str, output_handler=None) -> Tuple[str, str]:
        """Process a chunk of text immediately."""
        if not chunk:
            return "", ""
            
        async with self._buffer_lock:
            return self.process_and_write(chunk)
            
    async def flush(self, output_handler=None) -> Tuple[str, str]:
        """Flush buffer (no-op since we process immediately)."""
        return "", ""