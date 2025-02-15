# display/animations/dot_loader.py

import asyncio
import json
import time
from typing import Tuple

class AsyncDotLoader:
    """Async dot-loading animation for streaming responses."""
    def __init__(self, style, terminal, prompt="", no_animation=False):
        """Initialize dot loader with style, terminal, prompt, and animation flag."""
        self.style = style
        self.terminal = terminal
        self.prompt = prompt.rstrip('.?!')
        self.no_anim = no_animation

        # Set dot character based on prompt ending.
        self.dot_char = '.' if prompt.endswith('.') or not prompt.endswith(('?','!')) else prompt[-1]
        self.dots = int(prompt.endswith(('.', '?', '!')))

        # Initialize animation state.
        self.animation_complete = asyncio.Event()
        self.animation_task = None
        self.resolved = False
        self._stored_messages = []

    async def _animate(self):
        """Run dot animation until complete."""
        try:
            while not self.animation_complete.is_set():
                await self._write_loading_state()
                await asyncio.sleep(0.4)
                if self.resolved and self.dots == 3:
                    await self._write_loading_state()
                    self.terminal.write('\n\n')
                    break
                self.dots = min(self.dots + 1, 3) if self.resolved else (self.dots + 1) % 4
            self.animation_complete.set()
        except Exception as e:
            self.animation_complete.set()
            raise e

    async def _write_loading_state(self):
        """Update display with current loading state."""
        # Calculate how many lines our text takes based on terminal width
        total_length = len(self.prompt) + self.dots  # Length of prompt plus current dots
        lines_needed = (total_length + self.terminal.width - 1) // self.terminal.width
        
        # Move up to the start of our wrapped text block
        if lines_needed > 1:
            self.terminal.write(f"\033[{lines_needed - 1}A")
        
        # Clear and write from the beginning
        self.terminal.write(f"\r\033[J{self.prompt}{self.dot_char * self.dots}")
        await self._yield()

    async def _handle_message_chunk(self, chunk, first_chunk) -> Tuple[str, str]:
        """Process a message chunk and return (raw, styled) text."""
        raw = styled = ""
        if not (c := chunk.strip()).startswith("data: ") or c == "data: [DONE]":
            return raw, styled

        try:
            if txt := json.loads(c[6:])["choices"][0]["delta"].get("content", ""):
                if first_chunk:
                    self.resolved = True
                    if not self.no_anim:
                        await self.animation_complete.wait()
                if not self.animation_complete.is_set():
                    self._stored_messages.append((txt, time.time()))
                else:
                    r, s = await self.style.write_styled(txt)
                    raw = r
                    styled = s
                await asyncio.sleep(0.01)
        except json.JSONDecodeError:
            pass

        return raw, styled

    async def _process_stored_messages(self) -> Tuple[str, str]:
        """Process stored messages in order and return (raw, styled) text."""
        raw = styled = ""
        if self._stored_messages:
            self._stored_messages.sort(key=lambda x: x[1])
            for i, (text, ts) in enumerate(self._stored_messages):
                if i:
                    await asyncio.sleep(ts - self._stored_messages[i - 1][1])
                r, s = await self.style.write_styled(text)
                raw += r
                styled += s
            self._stored_messages.clear()
        return raw, styled

    async def run_with_loading(self, stream) -> Tuple[str, str]:
        """Run loading animation while processing message stream and return outputs."""
        if not self.style:
            raise ValueError("style must be provided")
        raw = styled = ""
        first_chunk = True
        if not self.no_anim:
            self.animation_task = asyncio.create_task(self._animate())
            await asyncio.sleep(0.01)
        try:
            if hasattr(stream, '__aiter__'):
                async for chunk in stream:
                    r, s = await self._handle_message_chunk(chunk, first_chunk)
                    raw += r
                    styled += s
                    first_chunk = False
            else:
                for chunk in stream:
                    r, s = await self._handle_message_chunk(chunk, first_chunk)
                    raw += r
                    styled += s
                    first_chunk = False
        finally:
            self.resolved = True
            self.animation_complete.set()
            if self.animation_task:
                await self.animation_task
            r, s = await self._process_stored_messages()
            raw += r
            styled += s
            r, s = await self.style.flush_styled()
            raw += r
            styled += s
            return raw, styled

    async def _yield(self):
        """Yield control to the event loop."""
        await asyncio.sleep(0)
