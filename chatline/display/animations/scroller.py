# display/animations/scroller.py

import asyncio
from typing import List, Optional

class Scroller:
    """Animate text scrolling with wrapping and formatting."""
    def __init__(self, style, terminal):
        """Init scroller with style engine and terminal."""
        self.style = style
        self.terminal = terminal

    def _handle_text(self, text: str, width: Optional[int] = None) -> List[str]:
        """Wrap text into lines, handling box-drawing chars."""
        width = width or self.terminal.width
        # If box-drawing chars present, split by newline.
        if any(ch in text for ch in ('╭', '╮', '╯', '╰')):
            return text.split('\n')
        result = []
        for para in text.split('\n'):
            if not para.strip():
                result.append('')
                continue
            line, words = '', para.split()
            for word in words:
                if len(word) > width:
                    if line:
                        result.append(line)
                    result.extend(word[i:i+width] for i in range(0, len(word), width))
                    line = ''
                else:
                    test = f"{line}{' ' if line else ''}{word}"
                    if self.style.get_visible_length(test) <= width:
                        line = test
                    else:
                        result.append(line)
                        line = word
            if line:
                result.append(line)
        return result

    async def _update_scroll_display(self, lines: List[str], prompt: str) -> None:
        """Clear screen and display lines with a prompt."""
        self.terminal.clear_screen()
        # Write each line.
        for line in lines:
            self.terminal.write(line, newline=True)
        # Write prompt with reset formatting.
        self.terminal.write(self.style.get_format('RESET'))
        self.terminal.write(prompt)

    async def scroll_up(self, styled_lines: str, prompt: str, delay: float = 0.5) -> None:
        """Scroll pre-styled text upward with a prompt and delay."""
        lines = self._handle_text(styled_lines)
        for i in range(len(lines) + 1):
            self.terminal.clear_screen()
            # Write remaining lines.
            for ln in lines[i:]:
                self.terminal.write(ln, newline=True)
            # Write prompt with reset formatting.
            self.terminal.write(self.style.get_format('RESET') + prompt)
            await asyncio.sleep(delay)