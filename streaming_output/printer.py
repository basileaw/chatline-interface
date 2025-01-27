# streaming_output/printer.py

import sys
from typing import Optional, List, Dict, Tuple
from streaming_output.painter import FORMATS
from utilities import (
    get_visible_length,
    handle_long_word,
    write_and_flush,
    get_terminal_width
)

class OutputHandler:
    """Handles terminal output management and word wrapping."""
    
    def __init__(self, text_painter):
        """
        Initialize OutputHandler with injected TextPainter.
        
        Args:
            text_painter: TextPainter instance for styling text
        """
        self.painter = text_painter
        self.current_line_length = 0
        self.word_buffer = ""

    def process_and_write(self, chunk: str) -> Tuple[str, str]:
        """Process and write a chunk of text with proper wrapping."""
        if not chunk:
            return ("", "")

        width = get_terminal_width()
        raw_out, styled_out = chunk, ""

        i = 0
        while i < len(chunk):
            char = chunk[i]

            if char.isspace():
                if self.word_buffer:
                    word_length = get_visible_length(self.word_buffer)
                    
                    if word_length > width:
                        word_chunks = handle_long_word(self.word_buffer, width)
                        for idx, word_chunk in enumerate(word_chunks):
                            if idx > 0:
                                write_and_flush("\n")
                                styled_out += "\n"
                                self.current_line_length = 0
                            
                            styled_chunk = self.painter.process_chunk(word_chunk)
                            write_and_flush(styled_chunk)
                            styled_out += styled_chunk
                            self.current_line_length = len(word_chunk)
                    else:
                        if self.current_line_length + word_length > width:
                            write_and_flush("\n")
                            styled_out += "\n"
                            self.current_line_length = 0
                        
                        styled_word = self.painter.process_chunk(self.word_buffer)
                        write_and_flush(styled_word)
                        styled_out += styled_word
                        self.current_line_length += word_length
                    
                    self.word_buffer = ""

                if char == '\n':
                    write_and_flush("\n")
                    styled_out += "\n"
                    self.current_line_length = 0
                elif self.current_line_length + 1 <= width:
                    write_and_flush(char)
                    styled_out += char
                    self.current_line_length += 1
            else:
                self.word_buffer += char

            i += 1

        sys.stdout.flush()
        return (raw_out, styled_out)

    def flush(self) -> Optional[str]:
        """Flush any remaining buffered content."""
        styled_out = ""
        
        if self.word_buffer:
            width = get_terminal_width()
            word_length = get_visible_length(self.word_buffer)
            
            if word_length > width:
                word_chunks = handle_long_word(self.word_buffer, width)
                for idx, chunk in enumerate(word_chunks):
                    if idx > 0:
                        write_and_flush("\n")
                        styled_out += "\n"
                    styled_chunk = self.painter.process_chunk(chunk)
                    write_and_flush(styled_chunk)
                    styled_out += styled_chunk
            else:
                if self.current_line_length + word_length > width:
                    write_and_flush("\n")
                    styled_out += "\n"
                styled_word = self.painter.process_chunk(self.word_buffer)
                write_and_flush(styled_word)
                styled_out += styled_word
            
            self.word_buffer = ""

        if self.current_line_length > 0:
            write_and_flush("\n")
            styled_out += "\n"

        write_and_flush(FORMATS['RESET'])
        sys.stdout.flush()
        self.painter.reset()
        self.current_line_length = 0

        return styled_out

class RawOutputHandler:
    """Simple pass-through handler for raw output."""
    def process_and_write(self, chunk: str) -> Tuple[str, str]:
        write_and_flush(chunk)
        return (chunk, chunk)
    def flush(self): pass