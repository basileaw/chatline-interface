# stream.py

import sys, asyncio
from typing import Tuple, Optional
from rich.console import Console
from rich.panel import Panel
from io import StringIO

class Stream:
    def __init__(self, styles, terminal=None):
        self.styles = styles
        self.terminal = terminal
        self._base_color = self.styles.get_format('RESET')
        self.active_patterns = []
        self.current_line_length = 0
        self.word_buffer = ""
        self._buffer_lock = asyncio.Lock()
        self._rich_console = Console(
            force_terminal=True,
            color_system="truecolor",
            file=StringIO(),
            highlight=False
        )

    def set_base_color(self, color: Optional[str] = None):
        if color: self._base_color = self.styles.get_color(color)
        else: self._base_color = self.styles.get_format('RESET')

    def _style_chunk(self, text: str) -> str:
        if not text: return ""
        if any(c in text for c in "╭╮╯╰│"): return text
        out = []
        if not self.active_patterns:
            out.append(
                f"{self.styles.get_format('ITALIC_OFF')}"
                f"{self.styles.get_format('BOLD_OFF')}{self._base_color}"
            )
        for i, ch in enumerate(text):
            if i == 0 or text[i-1].isspace():
                out.append(self.styles.get_style(self.active_patterns, self._base_color))
            if (self.active_patterns and ch in self.styles.end_map
                    and ch == self.styles.by_name[self.active_patterns[-1]].end):
                pat = self.styles.by_name[self.active_patterns[-1]]
                if not pat.remove_delimiters:
                    out.append(self.styles.get_style(self.active_patterns, self._base_color) + ch)
                self.active_patterns.pop()
                out.append(self.styles.get_style(self.active_patterns, self._base_color))
                continue
            if ch in self.styles.start_map:
                new_pat = self.styles.start_map[ch]
                self.active_patterns.append(new_pat.name)
                out.append(self.styles.get_style(self.active_patterns, self._base_color))
                if not new_pat.remove_delimiters: out.append(ch)
                continue
            out.append(ch)
        return "".join(out)

    async def add(self, chunk: str, output_handler=None) -> Tuple[str, str]:
        if not chunk: return "", ""
        async with self._buffer_lock:
            return self.process_and_write(chunk)

    def process_and_write(self, chunk: str) -> Tuple[str, str]:
        if not chunk: return "", ""
        styled_out = ""
        if self.terminal: self.terminal._hide_cursor()
        try:
            if any(c in chunk for c in "╭╮╯╰│"):
                sys.stdout.write(chunk)
                styled_out = chunk
            else:
                for char in chunk:
                    if char.isspace():
                        if self.word_buffer:
                            styled_word = self._style_chunk(self.word_buffer)
                            sys.stdout.write(styled_word)
                            styled_out += styled_word
                            self.word_buffer = ""
                        sys.stdout.write(char)
                        styled_out += char
                        self.current_line_length = 0 if char == '\n' else self.current_line_length + 1
                    else:
                        self.word_buffer += char
            sys.stdout.flush()
            return chunk, styled_out
        finally:
            if self.terminal: self.terminal._hide_cursor()

    async def flush(self, output_handler=None) -> Tuple[str, str]:
        styled_out = ""
        if self.terminal: self.terminal._hide_cursor()
        try:
            if self.word_buffer:
                styled_word = self._style_chunk(self.word_buffer)
                sys.stdout.write(styled_word)
                styled_out += styled_word
                self.word_buffer = ""
            if self.current_line_length > 0:
                sys.stdout.write("\n")
                styled_out += "\n"
            sys.stdout.write(self.styles.get_format('RESET'))
            sys.stdout.flush()
            self.reset()
            return "", styled_out
        finally:
            if self.terminal: self.terminal._hide_cursor()

    def reset(self):
        self.active_patterns.clear()
        self.word_buffer = ""
        self.current_line_length = 0
