# state/terminal.py
import asyncio, time
from typing import List, Optional
from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import FormattedText

class TerminalManager:
    def __init__(self, utilities):
        self.utils = utilities
        self.prompt_session = PromptSession()
        self._term_width = self.utils.get_terminal_width()

    async def _write(self, text: str = "", style: str = None, newline: bool = False):
        if style: self.utils.write_and_flush(self.utils.get_format(style))
        self.utils.write_and_flush(text)
        if style: self.utils.write_and_flush(self.utils.get_format('RESET'))
        if newline: self.utils.write_and_flush('\n')
        await asyncio.sleep(0)

    def _prepare_lines(self, text: str) -> List[str]:
        lines = []
        for para in text.split('\n'):
            if not para.strip():
                lines.append('')
                continue
            line = ''
            for word in para.split():
                test = line + (' ' if line else '') + word
                if self.utils.get_visible_length(test) <= self._term_width:
                    line = test
                else:
                    lines.append(line)
                    line = word
            if line: lines.append(line)
        return lines

    async def clear(self):
        self.utils.clear_screen()
        await asyncio.sleep(0)

    async def write_lines(self, lines: List[str], newline: bool = True):
        for line in lines:
            await self._write(line, newline=newline)

    async def write_prompt(self, prompt: str, style: Optional[str] = None):
        await self._write(prompt, style)

    async def scroll_up(self, text: str, prompt: str, delay: float = 0.5):
        lines = self._prepare_lines(text)
        for i in range(len(lines) + 1):
            await self.clear()
            await self.write_lines(lines[i:])
            await self.write_prompt(prompt, 'RESET')
            await asyncio.sleep(delay)

    async def update_display(self, content: str = None, prompt: str = None, 
                           preserve_cursor: bool = False):
        if not preserve_cursor: self.utils.hide_cursor()
        await self.clear()
        if content: await self.write_lines([content], bool(prompt))
        if prompt: await self.write_prompt(prompt)
        if not preserve_cursor: self.utils.show_cursor()

    async def write_loading_state(self, prompt: str, dots: int):
        await self._write(f"\r{' '*80}\r{prompt}{'.'*dots}")

    async def get_user_input(self, default_text: str = "", add_newline: bool = True) -> str:
        self.utils.show_cursor()
        if add_newline: await self._write("\n")
        result = await self.prompt_session.prompt_async(
            FormattedText([('class:prompt', '> ')]), 
            default=default_text
        )
        self.utils.hide_cursor()
        return result.strip()

    async def handle_scroll(self, styled_lines: str, prompt: str, delay: float = 0.5):
        lines = self._prepare_lines(styled_lines)
        for i in range(len(lines) + 1):
            self.utils.clear_screen()
            for ln in lines[i:]: await self._write(ln, newline=True)
            await self._write(self.utils.get_format('RESET') + prompt)
            time.sleep(delay)

    async def update_animated_display(self, content: str = "", preserved_msg: str = "", 
                                    no_spacing: bool = False):
        self.utils.clear_screen()
        if content:
            if preserved_msg:
                await self._write(preserved_msg + ("" if no_spacing else "\n\n"))
            await self._write(content)
        else:
            await self._write(preserved_msg)
        await self._write("", 'RESET')