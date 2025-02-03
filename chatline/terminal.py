# terminal.py

import asyncio, time, sys, shutil
from prompt_toolkit import PromptSession
from prompt_toolkit.validation import Validator, ValidationError
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.key_binding import KeyBindings

class Terminal:
    def __init__(self, styles):
        self.styles = styles
        self.term_width = shutil.get_terminal_size().columns
        self._is_edit_mode = False
        self._cursor_visible = True
        kb = KeyBindings()

        @kb.add('c-e')
        def _(event):
            if not self._is_edit_mode:
                event.current_buffer.text = "edit"
                event.app.exit(result=event.current_buffer.text)

        @kb.add('c-r')
        def _(event):
            if not self._is_edit_mode:
                event.current_buffer.text = "retry"
                event.app.exit(result=event.current_buffer.text)

        self.prompt_session = PromptSession(key_bindings=kb, complete_while_typing=False)

    def _is_terminal(self): return sys.stdout.isatty()
    async def _yield_to_event_loop(self): await asyncio.sleep(0)

    def _manage_cursor(self, show):
        if self._cursor_visible != show and self._is_terminal():
            self._cursor_visible = show
            sys.stdout.write("\033[?25h" if show else "\033[?25l")
            sys.stdout.flush()

    def _show_cursor(self): self._manage_cursor(True)
    def _hide_cursor(self): self._manage_cursor(False)

    def _write(self, text="", style=None, newline=False):
        self._hide_cursor()
        try:
            if style: sys.stdout.write(self.styles.get_format(style))
            sys.stdout.write(text)
            if style: sys.stdout.write(self.styles.get_format('RESET'))
            if newline: sys.stdout.write('\n')
            sys.stdout.flush()
        finally:
            self._hide_cursor()

    def _clear_screen(self):
        if self._is_terminal():
            sys.stdout.write("\033[2J\033[H")
            sys.stdout.flush()

    def _handle_text(self, text, width=None):
        width = width or self.term_width
        if any(x in text for x in ('╭','╮','╯','╰')): return text.split('\n')
        
        result = []
        for para in text.split('\n'):
            if not para.strip():
                result.append('')
                continue
            line, words = '', para.split()
            for word in words:
                if len(word) > width:
                    if line: result.append(line)
                    result.extend(word[i:i+width] for i in range(0, len(word), width))
                    line = ''
                else:
                    test = f"{line}{' ' if line else ''}{word}"
                    if self.styles.get_visible_length(test) <= width:
                        line = test
                    else:
                        result.append(line)
                        line = word
            if line: result.append(line)
        return result

    async def clear(self):
        self._clear_screen()
        await self._yield_to_event_loop()

    async def write_lines(self, lines, newline=True):
        for line in lines: self._write(line, newline=newline)
        await self._yield_to_event_loop()

    async def write_prompt(self, prompt, style=None):
        self._write(prompt, style)
        await self._yield_to_event_loop()

    async def write_loading_state(self, prompt, dots, dot_char='.'):
        self._write(f"\r{' '*80}\r{prompt}{dot_char*dots}")
        await self._yield_to_event_loop()

    async def update_display(self, content=None, prompt=None, preserve_cursor=False):
        if not preserve_cursor: self._hide_cursor()
        await self.clear()
        if content: await self.write_lines([content], bool(prompt))
        if prompt: await self.write_prompt(prompt)
        if not preserve_cursor: self._hide_cursor()

    async def update_animated_display(self, content="", preserved_msg="", no_spacing=False):
        self._clear_screen()
        if content:
            if preserved_msg: self._write(preserved_msg + ("" if no_spacing else "\n\n"))
            self._write(content)
        else:
            self._write(preserved_msg)
        self._write("", 'RESET')
        await self._yield_to_event_loop()

    async def scroll_up(self, text, prompt, delay=0.5):
        lines = self._handle_text(text)
        for i in range(len(lines)+1):
            await self.clear()
            await self.write_lines(lines[i:])
            await self.write_prompt(prompt, 'RESET')
            await asyncio.sleep(delay)

    async def handle_scroll(self, styled_lines, prompt, delay=0.5):
        lines = self._handle_text(styled_lines)
        for i in range(len(lines)+1):
            self._clear_screen()
            for ln in lines[i:]: self._write(ln, newline=True)
            self._write(self.styles.get_format('RESET')+prompt)
            time.sleep(delay)

    async def get_user_input(self, default_text="", add_newline=True):
        class NonEmptyValidator(Validator):
            def validate(self, document):
                if not document.text.strip():
                    raise ValidationError(message='', cursor_position=0)

        if add_newline: self._write("\n")
        self._is_edit_mode = bool(default_text)
        try:
            self._show_cursor()
            result = await self.prompt_session.prompt_async(
                FormattedText([('class:prompt','> ')]),
                default=default_text,
                validator=NonEmptyValidator(),
                validate_while_typing=False
            )
            return result.strip()
        finally:
            self._is_edit_mode = False
            self._hide_cursor()