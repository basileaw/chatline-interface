# display/animations/dot_loader.py

import asyncio
import json
import time
from typing import Tuple, Optional, List

class AsyncDotLoader:
    """
    Async dot-loading animation for streaming responses.
    
    Displays an animated loading indicator while content is being streamed,
    then smoothly transitions to displaying the content.
    """
    def __init__(self, style, terminal, prompt="", no_animation=False):
        """
        Initialize the dot loader animation.
        
        Args:
            style: StyleEngine instance for text styling
            terminal: DisplayTerminal instance for output
            prompt: Text to display before the dots
            no_animation: Whether to disable animation
        """
        self.style = style
        self.terminal = terminal
        self.prompt = prompt.rstrip('.?!')
        self.no_anim = no_animation
        
        # Determine dot character based on prompt ending
        self.dot_char = '.' if prompt.endswith('.') or not prompt.endswith(('?','!')) else prompt[-1]
        self.dots = int(prompt.endswith(('.', '?', '!')))
        
        # Animation state
        self.animation_complete = asyncio.Event()
        self.animation_task = None
        self.resolved = False
        self._stored_messages = []

    async def _animate(self):
        """Run the dot animation until completion."""
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
        """Update the loading state display."""
        self.terminal.write(f"\r{' ' * 80}\r{self.prompt}{self.dot_char * self.dots}")
        await self._yield()

    async def _handle_message_chunk(self, chunk, first_chunk) -> Tuple[str, str]:
        """
        Process a single message chunk.
        
        Args:
            chunk: Raw message chunk
            first_chunk: Whether this is the first chunk
            
        Returns:
            Tuple of (raw_text, styled_text)
        """
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
                    r2, s2 = await self.style.write_styled(txt)
                    raw = r + r2
                    styled = s + s2
                    
                await asyncio.sleep(0.01)
        except json.JSONDecodeError:
            pass
            
        return raw, styled

    async def _process_stored_messages(self) -> Tuple[str, str]:
        """
        Process all stored messages in chronological order.
        
        Returns:
            Tuple of (raw_text, styled_text)
        """
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
        """
        Run loading animation while processing the stream.
        
        Args:
            stream: Iterator or async iterator of message chunks
            
        Returns:
            Tuple of (raw_output, styled_output)
            
        Raises:
            ValueError: If style is not provided
        """
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
        """Yield briefly to the event loop."""
        await asyncio.sleep(0)