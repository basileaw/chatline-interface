# output_handler.py

import sys
import shutil
import re
from dataclasses import dataclass
from typing import Optional, List, Dict

# ANSI Format Codes
FORMATS = {
    'RESET': '\033[0m',
    'ITALIC_ON': '\033[3m',
    'ITALIC_OFF': '\033[23m'
}

# Example color palette
COLORS = {
    'GREEN': '\033[38;5;47m',
    'PINK': '\033[38;5;212m',
    'BLUE': '\033[38;5;75m'
}

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
    Accumulate partial tokens from streaming, finalize lines only when:
      - we see a newline (`\n`), or
      - the line would exceed terminal width if we add more text.

    Then apply pattern-based ANSI styling and print the lines.
    """
    ANSI_REGEX = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')

    def __init__(self, patterns: List[Dict] = None, base_color: str = COLORS['GREEN']):
        # Base style
        self.base_color = base_color

        # Default patterns
        default_patterns = [
            {
                'name': 'quotes',
                'start': '"',
                'end': '"',
                'color': COLORS['PINK'],
                'italic': False,
                'remove_delimiters': False
            },
            {
                'name': 'brackets',
                'start': '[',
                'end': ']',
                'color': COLORS['BLUE'],
                'italic': False,
                'remove_delimiters': False
            },
            {
                'name': 'emphasis',
                'start': '_',
                'end': '_',
                'color': None,
                'italic': True,
                'remove_delimiters': True
            }
        ]
        self.patterns = [Pattern(**p) for p in (patterns or default_patterns)]

        # Ensure no overlapping delimiters
        used_chars = set()
        for pat in self.patterns:
            if pat.start in used_chars or pat.end in used_chars:
                raise ValueError(f"Pattern '{pat.name}' reuses a delimiter: {pat.start} or {pat.end}")
            used_chars.update([pat.start, pat.end])

        self.by_name = {p.name: p for p in self.patterns}
        self.start_map = {p.start: p for p in self.patterns}
        self.end_map = {p.end: p for p in self.patterns}

        # Track currently active patterns (for nested coloring/italics)
        self.active_patterns: List[str] = []

        # Buffer for partial tokens that haven't formed a complete line yet
        self.partial_buffer = ""

    def get_style(self) -> str:
        """
        Combine active patterns to produce color + possibly italic.
        """
        color = self.base_color
        italic = False
        for name in self.active_patterns:
            pat = self.by_name[name]
            if pat.color:
                color = pat.color
            if pat.italic:
                italic = True

        # Return italic ON if needed, else force italic OFF
        return (FORMATS['ITALIC_ON'] if italic else FORMATS['ITALIC_OFF']) + color

    def process_chunk_for_ansi(self, text: str) -> str:
        """
        Insert ANSI codes for patterns (quotes, brackets, underscores).
        No line-wrapping logic here—just styling.
        """
        if not text:
            return ""

        output = []
        i = 0
        if not self.active_patterns:
            # Start with our base style if no patterns are open
            output.append(FORMATS['ITALIC_OFF'] + self.base_color)

        while i < len(text):
            ch = text[i]

            # If we just started or the previous char was whitespace, refresh style
            if i == 0 or text[i-1].isspace():
                output.append(self.get_style())

            # Check if we close the most recent pattern
            if self.active_patterns and ch in self.end_map \
               and ch == self.by_name[self.active_patterns[-1]].end:
                current_pat = self.by_name[self.active_patterns[-1]]
                if not current_pat.remove_delimiters:
                    output.append(self.get_style() + ch)
                self.active_patterns.pop()
                # Re-apply the style of what's still open
                output.append(self.get_style())
                i += 1
                continue

            # Check if we open a new pattern
            if ch in self.start_map:
                new_pat = self.start_map[ch]
                self.active_patterns.append(new_pat.name)
                output.append(self.get_style())
                if not new_pat.remove_delimiters:
                    output.append(ch)
                i += 1
                continue

            # Otherwise just append the character
            output.append(ch)
            i += 1

        return "".join(output)

    def get_visible_length(self, text: str) -> int:
        """
        Returns the length of `text` ignoring ANSI escape codes.
        """
        return len(self.ANSI_REGEX.sub('', text))

    def wrap_line(self, line: str, width: int) -> List[str]:
        """
        Splits a single line (ANSI-styled) by whitespace into sub-lines
        that don't exceed the given width in visible characters.
        Returns each sub-line with a trailing `\n`.
        """
        words = line.split()
        if not words:
            # blank line => return it as-is
            return ["\n"]

        wrapped = []
        current_line = ""
        for w in words:
            if not current_line:
                current_line = w
            else:
                test_line = current_line + " " + w
                if self.get_visible_length(test_line) <= width:
                    current_line = test_line
                else:
                    wrapped.append(current_line + "\n")
                    current_line = w

        if current_line:
            wrapped.append(current_line + "\n")
        return wrapped

    def _extract_one_line(self, buffer_text: str, width: int):
        """
        Try to extract exactly one "finalized line" from buffer_text.
        A line is finalized if:
          - We find a newline `\n`, or
          - We exceed `width` with the next word.

        Returns (line, leftover_buffer).
        If no full line is found (neither newline nor width exceeded),
        returns (None, buffer_text).
        """
        # 1) If there's an explicit newline, we finalize everything up to that
        newline_idx = buffer_text.find("\n")
        if newline_idx != -1:
            line = buffer_text[:newline_idx]
            leftover = buffer_text[newline_idx+1:]
            return (line, leftover)

        # 2) If no newline, see if adding words would exceed `width`
        # We'll accumulate words until we exceed `width`
        words = re.finditer(r'\S+|\s+', buffer_text)  # tokens including spaces

        current_line = ""
        last_used_idx = 0
        for match in words:
            token = match.group(0)
            test_line = current_line + token
            if self.get_visible_length(test_line) > width:
                # if we never added anything, that means the token alone is bigger than width
                # We'll forcibly break on this token
                if not current_line:
                    # forcibly finalize this token
                    # strip the trailing spaces
                    line = token.strip()
                    leftover = buffer_text[match.end():]
                    return (line, leftover)
                else:
                    # finalize what we had
                    line = current_line.strip()
                    leftover = buffer_text[last_used_idx:]
                    return (line, leftover)
            else:
                # accept token
                current_line = test_line
                last_used_idx = match.end()

        # If we finish the loop and never exceed width or hit newline,
        # we can't finalize a line yet => return (None, buffer_text)
        return (None, buffer_text)

    def process_and_write(self, chunk: str) -> tuple[str, str]:
        """
        Accumulate this chunk in self.partial_buffer,
        repeatedly extract finalized lines, style/wrap them, output them.
        Returns (raw_text, styled_text) that was actually discharged.
        """
        if not chunk:
            return ("", "")

        self.partial_buffer += chunk

        width = shutil.get_terminal_size().columns
        finalized_lines = []
        while True:
            line, leftover = self._extract_one_line(self.partial_buffer, width)
            if line is None:
                break
            finalized_lines.append(line)
            self.partial_buffer = leftover

        raw_discharged = ""
        styled_discharged = ""

        for ln in finalized_lines:
            raw_discharged += ln + "\n"
            # Style the line
            styled_line = self.process_chunk_for_ansi(ln)
            # Wrap the line again ignoring ANSI
            wrapped_lines = self.wrap_line(styled_line, width)
            final_text = "".join(wrapped_lines)
            sys.stdout.write(final_text)
            sys.stdout.flush()
            styled_discharged += final_text

        return (raw_discharged, styled_discharged)

    def flush(self):
        """
        Emit any leftover partial text as final lines, then reset.
        Prevents losing the final line if it never got a newline.
        Also clears partial_buffer.
        """
        leftover = self.partial_buffer
        self.partial_buffer = ""

        width = shutil.get_terminal_size().columns
        lines_to_output = []

        # Repeatedly extract lines until none remain
        while True:
            line, leftover = self._extract_one_line(leftover, width)
            if line is None:
                break
            lines_to_output.append(line)

        # If there's leftover text that didn't form a "full line," treat it as one line
        # (Unless it's pure whitespace, we can discard or keep it as you prefer.)
        if leftover.strip():
            lines_to_output.append(leftover.strip())

        # Now style + output each line
        for ln in lines_to_output:
            styled_line = self.process_chunk_for_ansi(ln)
            wrapped_lines = self.wrap_line(styled_line, width)
            sys.stdout.write("".join(wrapped_lines))

        # Reset ANSI codes, just in case
        sys.stdout.write(FORMATS['RESET'] + "\n")
        sys.stdout.flush()

        # Optionally also reset any open patterns
        self.active_patterns.clear()


class RawOutputHandler:
    def __init__(self):
        pass

    def process_and_write(self, chunk: str) -> tuple[str, str]:
        sys.stdout.write(chunk)
        sys.stdout.flush()
        return (chunk, chunk)

    def flush(self):
        pass


if __name__ == '__main__':

    def main():
        oh = OutputHandler()

        # Simulate a streaming scenario
        chunks = [
            "Hi t",
            "here! I'm an AI as",
            "sistant.\nDesigned to help and chat ",
            "with you.\nAlways eager to learn and explore"
        ]

        for c in chunks:
            oh.process_and_write(c)

        # End of stream => flush leftover partial
        oh.flush()

        print("\n--- Demo Complete ---\n")

    main()
