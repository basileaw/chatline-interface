import sys
import shutil
import re
from dataclasses import dataclass
from typing import Optional, List, Dict

# Minimal ANSI codes + colors
FORMATS = {'RESET': '\033[0m', 'ITALIC_ON': '\033[3m', 'ITALIC_OFF': '\033[23m'}
COLORS = {'GREEN': '\033[38;5;47m', 'PINK': '\033[38;5;212m', 'BLUE': '\033[38;5;75m'}

@dataclass
class Pattern:
    name: str
    start: str
    end: str
    color: Optional[str]
    italic: bool
    remove_delimiters: bool

class OutputHandler:
    """
    Streams text chunks with immediate output, handling ANSI formatting 
    and word wrapping dynamically.
    """
    ANSI_REGEX = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')

    def __init__(self, patterns: List[Dict]=None, base_color=COLORS['GREEN']):
        default_patterns = [
            {'name': 'quotes', 'start': '"', 'end': '"', 'color': COLORS['PINK'], 'italic': False, 'remove_delimiters': False},
            {'name': 'brackets', 'start': '[', 'end': ']', 'color': COLORS['BLUE'], 'italic': False, 'remove_delimiters': False},
            {'name': 'emphasis', 'start': '_', 'end': '_', 'color': None, 'italic': True, 'remove_delimiters': True}
        ]
        self.patterns = [Pattern(**p) for p in (patterns or default_patterns)]
        self.base_color = base_color
        self.active_patterns: List[str] = []
        self.current_line_length = 0  # Track visible length of current line
        self.word_buffer = ""  # Buffer for partial words

        # Checks for overlapping delimiters
        used = set()
        for p in self.patterns:
            if p.start in used or p.end in used:
                raise ValueError(f"Duplicate delimiter in '{p.name}'")
            used.update([p.start, p.end])

        self.by_name = {p.name: p for p in self.patterns}
        self.start_map = {p.start: p for p in self.patterns}
        self.end_map = {p.end: p for p in self.patterns}

    def get_style(self) -> str:
        color = self.base_color
        italic = False
        for name in self.active_patterns:
            pat = self.by_name[name]
            if pat.color: color = pat.color
            if pat.italic: italic = True
        return (FORMATS['ITALIC_ON'] if italic else FORMATS['ITALIC_OFF']) + color

    def process_chunk_for_ansi(self, text: str) -> str:
        if not text: return ""
        out, i = [], 0
        if not self.active_patterns:
            out.append(FORMATS['ITALIC_OFF'] + self.base_color)
        while i < len(text):
            ch = text[i]
            if i == 0 or text[i-1].isspace():
                out.append(self.get_style())
            if self.active_patterns and ch in self.end_map:
                if ch == self.by_name[self.active_patterns[-1]].end:
                    pat = self.by_name[self.active_patterns[-1]]
                    if not pat.remove_delimiters: out.append(self.get_style()+ch)
                    self.active_patterns.pop()
                    out.append(self.get_style()); i+=1; continue
            if ch in self.start_map:
                new_pat = self.start_map[ch]
                self.active_patterns.append(new_pat.name)
                out.append(self.get_style())
                if not new_pat.remove_delimiters: out.append(ch)
                i+=1; continue
            out.append(ch); i+=1
        return "".join(out)

    def get_visible_length(self, txt: str) -> int:
        return len(self.ANSI_REGEX.sub('', txt))

    def handle_long_word(self, word: str, width: int) -> List[str]:
        """Split a word that exceeds terminal width into chunks."""
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
                # Process any buffered word when we hit a space
                if self.word_buffer:
                    word_length = self.get_visible_length(self.word_buffer)
                    
                    # Handle words that exceed terminal width
                    if word_length > width:
                        word_chunks = self.handle_long_word(self.word_buffer, width)
                        for idx, word_chunk in enumerate(word_chunks):
                            if idx > 0:  # Not first chunk
                                sys.stdout.write("\n")
                                styled_out += "\n"
                                self.current_line_length = 0
                            
                            styled_chunk = self.process_chunk_for_ansi(word_chunk)
                            sys.stdout.write(styled_chunk)
                            styled_out += styled_chunk
                            self.current_line_length = len(word_chunk)
                    else:
                        # Normal word processing
                        if self.current_line_length + word_length > width:
                            sys.stdout.write("\n")
                            styled_out += "\n"
                            self.current_line_length = 0
                        
                        styled_word = self.process_chunk_for_ansi(self.word_buffer)
                        sys.stdout.write(styled_word)
                        styled_out += styled_word
                        self.current_line_length += word_length
                    
                    self.word_buffer = ""

                # Handle the space character itself
                if char == '\n':
                    sys.stdout.write("\n")
                    styled_out += "\n"
                    self.current_line_length = 0
                elif self.current_line_length + 1 <= width:
                    sys.stdout.write(char)
                    styled_out += char
                    self.current_line_length += 1

            else:
                # Add character to word buffer
                self.word_buffer += char

            i += 1

        sys.stdout.flush()
        return (raw_out, styled_out)

    def flush(self):
        """Flush any remaining buffered content and ensure proper spacing."""
        if self.word_buffer:
            width = shutil.get_terminal_size().columns
            word_length = self.get_visible_length(self.word_buffer)
            
            if word_length > width:
                word_chunks = self.handle_long_word(self.word_buffer, width)
                for idx, chunk in enumerate(word_chunks):
                    if idx > 0:
                        sys.stdout.write("\n")
                    styled_chunk = self.process_chunk_for_ansi(chunk)
                    sys.stdout.write(styled_chunk)
            else:
                if self.current_line_length + word_length > width:
                    sys.stdout.write("\n")
                styled_word = self.process_chunk_for_ansi(self.word_buffer)
                sys.stdout.write(styled_word)
            
            self.word_buffer = ""

        # Always ensure a newline at the end of response
        if self.current_line_length > 0:  # If we're not already at the start of a line
            sys.stdout.write("\n")

        
        sys.stdout.write(FORMATS['RESET'])
        sys.stdout.flush()
        self.active_patterns.clear()
        self.current_line_length = 0

class RawOutputHandler:
    """Simple pass-through handler for raw output."""
    def process_and_write(self, chunk: str) -> tuple[str, str]:
        sys.stdout.write(chunk)
        sys.stdout.flush()
        return (chunk, chunk)
    def flush(self): pass

if __name__ == '__main__':
    def main():
        oh = OutputHandler()
        test_chunks = [
            "Hi t", "here! I'm an AI as",
            "sistant.\nDesigned to help and chat ",
            "with you.\nAlways eager to learn and explore new things. ",
            "Here's a really_really_really_really_really_really_long_word_without_spaces to test wrapping."
        ]
        for c in test_chunks:
            oh.process_and_write(c)
        oh.flush()
        print("\n--- Done ---")

    main()