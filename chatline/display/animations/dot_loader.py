# display/animations/dot_loader.py

import asyncio
import json
import time

class AsyncDotLoader:
    """Async dot-loading animation during streaming."""
    def __init__(self, styles, prompt="", no_animation=False):
        self.styles = styles
        self.prompt = prompt.rstrip('.?!')
        self.no_anim = no_animation
        self.dot_char = '.' if prompt.endswith('.') or not prompt.endswith(('?','!')) else prompt[-1]
        self.dots = int(prompt.endswith(('.', '?', '!')))
        self.animation_complete = asyncio.Event()
        self.animation_task = None
        self.resolved = False
        self.utilities = None  # Set by DisplayAnimations
        self._stored_messages = []

    async def _animate(self):
        """Animate dots until loading completes."""
        try:
            while not self.animation_complete.is_set():
                await self.utilities.write_loading_state(self.prompt, self.dots, self.dot_char)
                await asyncio.sleep(0.4)
                if self.resolved and self.dots == 3:
                    await self.utilities.write_loading_state(self.prompt, 3, self.dot_char)
                    self.utilities.terminal.write('\n\n')
                    break
                self.dots = min(self.dots + 1, 3) if self.resolved else (self.dots + 1) % 4
            self.animation_complete.set()
        except Exception as e:
            self.animation_complete.set()
            raise e

    async def _handle_message_chunk(self, chunk, first_chunk):
        """Process a single message chunk."""
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
                    r, s = await self._process_stored_messages()
                    r2, s2 = await self.styles.write_styled(txt)
                    raw = r + r2
                    styled = s + s2
                await asyncio.sleep(0.01)
        except json.JSONDecodeError:
            pass
        return raw, styled

    async def _process_stored_messages(self):
        """Process stored messages in order."""
        raw = styled = ""
        if self._stored_messages:
            self._stored_messages.sort(key=lambda x: x[1])
            for i, (text, ts) in enumerate(self._stored_messages):
                if i:
                    await asyncio.sleep(ts - self._stored_messages[i - 1][1])
                r, s = await self.styles.write_styled(text)
                raw += r
                styled += s
            self._stored_messages.clear()
        return raw, styled

    async def run_with_loading(self, stream):
        """
        Run loading animation while processing the stream.
        
        Args:
            stream: Iterator or async iterator of message chunks.
        Returns:
            Tuple of (raw_output, styled_output)
        """
        if not self.styles:
            raise ValueError("styles must be provided")
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
            r, s = await self.styles.flush_styled()
            raw += r
            styled += s
            return raw, styled
