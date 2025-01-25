# output_handler.py

import sys
import shutil
import re
from typing import Optional, List, Dict
from painter import TextPainter, FORMATS, COLORS, Pattern

class OutputHandler:
    """Handles terminal output management and word wrapping."""
    ANSI_REGEX = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')

    def __init__(self, patterns: List[Dict] = None, base_color=COLORS['GREEN']):
        self.painter = TextPainter(patterns, base_color)
        self.current_line_length = 0
        self.word_buffer = ""

    def get_visible_length(self, txt: str) -> int:
        return len(self.ANSI_REGEX.sub('', txt))

    def handle_long_word(self, word: str, width: int) -> List[str]:
        chunks = []
        while word:
            if len(word) <= width:
                chunks.append(word)
                break
            chunks.append(word[:width])
            word = word[width:]
        return chunks

    def process_and_write(self, chunk: str) -> tuple[str, str]:
        if not chunk:
            return ("", "")

        width = shutil.get_terminal_size().columns
        raw_out, styled_out = chunk, ""

        i = 0
        while i < len(chunk):
            char = chunk[i]

            if char.isspace():
                if self.word_buffer:
                    word_length = self.get_visible_length(self.word_buffer)
                    
                    if word_length > width:
                        word_chunks = self.handle_long_word(self.word_buffer, width)
                        for idx, word_chunk in enumerate(word_chunks):
                            if idx > 0:
                                sys.stdout.write("\n")
                                styled_out += "\n"
                                self.current_line_length = 0
                            
                            styled_chunk = self.painter.process_chunk(word_chunk)
                            sys.stdout.write(styled_chunk)
                            styled_out += styled_chunk
                            self.current_line_length = len(word_chunk)
                    else:
                        if self.current_line_length + word_length > width:
                            sys.stdout.write("\n")
                            styled_out += "\n"
                            self.current_line_length = 0
                        
                        styled_word = self.painter.process_chunk(self.word_buffer)
                        sys.stdout.write(styled_word)
                        styled_out += styled_word
                        self.current_line_length += word_length
                    
                    self.word_buffer = ""

                if char == '\n':
                    sys.stdout.write("\n")
                    styled_out += "\n"
                    self.current_line_length = 0
                elif self.current_line_length + 1 <= width:
                    sys.stdout.write(char)
                    styled_out += char
                    self.current_line_length += 1
            else:
                self.word_buffer += char

            i += 1

        sys.stdout.flush()
        return (raw_out, styled_out)

    def flush(self):
        styled_out = ""
        
        if self.word_buffer:
            width = shutil.get_terminal_size().columns
            word_length = self.get_visible_length(self.word_buffer)
            
            if word_length > width:
                word_chunks = self.handle_long_word(self.word_buffer, width)
                for idx, chunk in enumerate(word_chunks):
                    if idx > 0:
                        sys.stdout.write("\n")
                        styled_out += "\n"
                    styled_chunk = self.painter.process_chunk(chunk)
                    sys.stdout.write(styled_chunk)
                    styled_out += styled_chunk
            else:
                if self.current_line_length + word_length > width:
                    sys.stdout.write("\n")
                    styled_out += "\n"
                styled_word = self.painter.process_chunk(self.word_buffer)
                sys.stdout.write(styled_word)
                styled_out += styled_word
            
            self.word_buffer = ""

        if self.current_line_length > 0:
            sys.stdout.write("\n")
            styled_out += "\n"

        sys.stdout.write(FORMATS['RESET'])
        sys.stdout.flush()
        self.painter.reset()
        self.current_line_length = 0

        return styled_out

class RawOutputHandler:
    """Simple pass-through handler for raw output."""
    def process_and_write(self, chunk: str) -> tuple[str, str]:
        sys.stdout.write(chunk)
        sys.stdout.flush()
        return (chunk, chunk)
    def flush(self): pass