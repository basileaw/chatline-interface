# dot_loader.py

import sys
import time
import threading
import asyncio
import json
from typing import Tuple, List, Any
from output_handler import OutputHandler, RawOutputHandler
from painter import FORMATS
from utilities import (
    hide_cursor,
    show_cursor,
    write_and_flush
)

class DotLoader:
    """
    Handles loading animation with dots while processing streamed content.
    Provides visual feedback during processing and manages content buffering.
    """
    
    def __init__(self, prompt: str, adaptive_buffer: Any = None, 
                 interval: float = 0.4, output_handler: Any = None, 
                 reuse_prompt: bool = False, no_animation: bool = False):
        """
        Initialize the dot loader.
        
        Args:
            prompt: The prompt text to display
            adaptive_buffer: Buffer instance for managing text flow
            interval: Animation interval in seconds
            output_handler: Handler for text output
            reuse_prompt: Whether to reuse the prompt line
            no_animation: Whether to disable animation
        """
        if prompt.endswith(("?", "!")):
            self.prompt = prompt[:-1]
            self.dot_char = prompt[-1]
            self.dots = 1
        elif prompt.endswith("."):
            self.prompt = prompt[:-1]
            self.dot_char = "."
            self.dots = 1
        else:
            self.prompt = prompt
            self.dot_char = "."
            self.dots = 0
            
        self.interval = interval
        self.resolved = False
        self.anim_done = threading.Event()
        self.stop_evt = threading.Event()
        self.th = None
        self.out = output_handler or RawOutputHandler()
        self.reuse = reuse_prompt
        self.no_anim = no_animation
        self.buffer = adaptive_buffer

    def _animate(self) -> None:
        """Run the dot animation in a separate thread."""
        hide_cursor()
        try:
            while not self.stop_evt.is_set():
                # Clear line and write current state
                if self.reuse:
                    write_and_flush(f"\r{' '*80}\r{self.prompt}{self.dot_char*self.dots}")
                else:
                    write_and_flush(f"\r{' '*80}\r{self.prompt}{self.dot_char*self.dots}")

                # Handle animation completion
                if self.resolved and self.dots == 3:
                    if not self.reuse:
                        write_and_flush(f"\r{' '*80}\r{self.prompt}{self.dot_char*3}\n\n")
                    else:
                        write_and_flush(f"\r{' '*80}\r{self.prompt}{self.dot_char*3}\033[2B")
                    time.sleep(self.interval)
                    self.anim_done.set()
                    break
                    
                # Update dot count
                if self.resolved:
                    self.dots = min(self.dots + 1, 3)
                else:
                    self.dots = (self.dots + 1) % 4
                    
                time.sleep(self.interval)
                
        except Exception:
            hide_cursor()
            raise

    async def _replay_chunks(self, stored: List[Tuple[str, float]]) -> Tuple[str, str]:
        """Replay stored chunks through the buffer with original timing."""
        if not stored:
            return "", ""
            
        stored.sort(key=lambda x: x[1])
        raw_acc, style_acc = "", ""
        
        for i, (txt, ts) in enumerate(stored):
            if i > 0:
                await asyncio.sleep(ts - stored[i-1][1])
            raw, styled = await self.buffer.add(txt, self.out)
            raw_acc += raw
            style_acc += styled
            
        return raw_acc, style_acc

    async def run_with_loading(self, stream: Any) -> Tuple[str, str]:
        """Process a stream of content with loading animation."""
        if not self.buffer:
            raise ValueError("AdaptiveBuffer must be provided")
            
        raw, styled = "", ""
        stored = []
        store_mode = True
        first_chunk = True

        if not self.no_anim:
            self.th = threading.Thread(target=self._animate, daemon=True)
            self.th.start()

        try:
            for chunk in stream:
                c = chunk.strip()
                if c == "data: [DONE]":
                    break
                
                if c.startswith("data: "):
                    try:
                        data = json.loads(c[6:])
                        txt = data["choices"][0]["delta"].get("content", "")
                        if txt:
                            if first_chunk:
                                self.resolved = True
                                if not self.no_anim:
                                    await asyncio.get_event_loop().run_in_executor(None, self.anim_done.wait)
                                first_chunk = False
                            
                            now = time.time()
                            if store_mode:
                                if not self.anim_done.is_set():
                                    stored.append((txt, now))
                                else:
                                    store_mode = False
                                    r1, s1 = await self._replay_chunks(stored)
                                    raw += r1
                                    styled += s1
                                    stored.clear()
                                    r2, s2 = await self.buffer.add(txt, self.out)
                                    raw += r2
                                    styled += s2
                            else:
                                r3, s3 = await self.buffer.add(txt, self.out)
                                raw += r3
                                styled += s3
                            
                            await asyncio.sleep(0.01)
                            
                    except json.JSONDecodeError:
                        pass
                        
                await asyncio.sleep(0)
                
        finally:
            self.stop_evt.set()
            if not self.no_anim and self.th and self.th.is_alive():
                self.th.join()
                
            if store_mode:
                r4, s4 = await self._replay_chunks(stored)
                raw += r4
                styled += s4
                
            rr, ss = await self.buffer.flush(self.out)
            raw += rr
            styled += ss
            
            if hasattr(self.out, 'flush'):
                final_styled = self.out.flush()
                if final_styled:
                    styled += final_styled
                    
            if isinstance(self.out, OutputHandler):
                write_and_flush(FORMATS['RESET'])
                
            return raw, styled