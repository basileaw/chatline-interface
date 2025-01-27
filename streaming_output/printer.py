# printer.py

import sys
from typing import Optional, List, Dict, Tuple

class OutputHandler:
    """Handles terminal output management and word wrapping."""
    
    def __init__(self, painter, utilities):
        """
        Initialize OutputHandler with injected dependencies.
        
        Args:
            painter: Painter instance for styling text
            utilities: Utilities instance for terminal operations
        """
        self.painter = painter
        self.utils = utilities
        self.current_line_length = 0
        self.word_buffer = ""

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
                            
                            styled_chunk = self.painter.process_chunk(word_chunk)
                            self.utils.write_and_flush(styled_chunk)
                            styled_out += styled_chunk
                            self.current_line_length = len(word_chunk)
                    else:
                        if self.current_line_length + word_length > width:
                            self.utils.write_and_flush("\n")
                            styled_out += "\n"
                            self.current_line_length = 0
                        
                        styled_word = self.painter.process_chunk(self.word_buffer)
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

    def flush(self) -> Optional[str]:
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
                    styled_chunk = self.painter.process_chunk(chunk)
                    self.utils.write_and_flush(styled_chunk)
                    styled_out += styled_chunk
            else:
                if self.current_line_length + word_length > width:
                    self.utils.write_and_flush("\n")
                    styled_out += "\n"
                styled_word = self.painter.process_chunk(self.word_buffer)
                self.utils.write_and_flush(styled_word)
                styled_out += styled_word
            
            self.word_buffer = ""

        if self.current_line_length > 0:
            self.utils.write_and_flush("\n")
            styled_out += "\n"

        self.utils.write_and_flush(self.painter.get_format('RESET'))
        sys.stdout.flush()
        self.painter.reset()
        self.current_line_length = 0

        return styled_out

class RawOutputHandler:
    """Simple pass-through handler for raw output."""
    def __init__(self, utilities):
        self.utils = utilities
        
    def process_and_write(self, chunk: str) -> Tuple[str, str]:
        self.utils.write_and_flush(chunk)
        return (chunk, chunk)
        
    def flush(self): pass