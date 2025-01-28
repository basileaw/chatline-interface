# state/animations.py

import asyncio
import json
import time
from dataclasses import dataclass
from typing import List, Protocol, Optional, Any, Tuple

class Buffer(Protocol):
    async def add(self, chunk: str, output_handler: Any) -> Tuple[str, str]: ...
    async def flush(self, output_handler: Any) -> Tuple[str, str]: ...
    def reset(self) -> None: ...

class AsyncDotLoader:
    """Handles loading animation with dots."""
    
    def __init__(self, utilities, prompt: str, adaptive_buffer: Optional[Buffer]=None,
                 interval=0.4, output_handler: Optional[Any]=None,
                 reuse_prompt=False, no_animation=False):
        self.utils = utilities
        self.out = output_handler
        self.buffer = adaptive_buffer
        self.interval = interval
        self.reuse = reuse_prompt
        self.no_anim = no_animation
        self.animation_task = None
        self.animation_complete = asyncio.Event()
        self.resolved = False
        
        # Process the prompt
        suffix = prompt[-1] if prompt else ""
        if suffix in ("?", "!"):
            self.prompt = prompt[:-1]
            self.dot_char = suffix
            self.dots = 1
        elif suffix == ".":
            self.prompt = prompt[:-1]
            self.dot_char = "."
            self.dots = 1
        else:
            self.prompt = prompt
            self.dot_char = "."
            self.dots = 0

    async def _animate(self) -> None:
        """Animate the loading dots."""
        self.utils.hide_cursor()
        try:
            self.utils.write_and_flush(f"\r{' '*80}\r{self.prompt}{self.dot_char*self.dots}")
            while not self.animation_complete.is_set():
                await asyncio.sleep(self.interval)
                if self.resolved and self.dots == 3:
                    seq = "\n\n" if not self.reuse else "\033[2B"
                    self.utils.write_and_flush(f"\r{' '*80}\r{self.prompt}{self.dot_char*3}{seq}")
                    self.animation_complete.set()
                    break
                self.dots = min(self.dots + 1, 3) if self.resolved else (self.dots + 1) % 4
                self.utils.write_and_flush(f"\r{' '*80}\r{self.prompt}{self.dot_char*self.dots}")
        finally:
            self.utils.show_cursor()

    async def _replay_chunks(self, stored: List[Tuple[str,float]]) -> Tuple[str,str]:
        """Replay stored chunks with timing."""
        if not stored:
            return "", ""
        stored.sort(key=lambda x: x[1])
        raw_acc, style_acc = "", ""
        for i, (txt, ts) in enumerate(stored):
            if i:
                await asyncio.sleep(ts - stored[i-1][1])
            raw, styled = await self.buffer.add(txt, self.out)
            raw_acc += raw
            style_acc += styled
        return raw_acc, style_acc

    async def run_with_loading(self, stream: Any) -> Tuple[str, str]:
        """Run the loading animation while processing the stream."""
        if not self.buffer:
            raise ValueError("AdaptiveBuffer must be provided")
            
        raw, styled = "", ""
        stored, store_mode = [], True
        first_chunk = True
        
        if not self.no_anim:
            self.animation_task = asyncio.create_task(self._animate())
            await asyncio.sleep(0.01)
            
        try:
            for chunk in stream:
                c = chunk.strip()
                if c == "data: [DONE]":
                    break
                    
                if c.startswith("data: "):
                    try:
                        data = json.loads(c[6:])
                        txt = data["choices"][0]["delta"].get("content","")
                        if txt:
                            if first_chunk:
                                self.resolved = True
                                if not self.no_anim:
                                    await self.animation_complete.wait()
                                first_chunk = False
                                
                            now = time.time()
                            if store_mode:
                                if not self.animation_complete.is_set():
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
            self.resolved = True
            self.animation_complete.set()
            if self.animation_task:
                await self.animation_task
            if store_mode:
                r4, s4 = await self._replay_chunks(stored)
                raw += r4
                styled += s4
            rr, ss = await self.buffer.flush(self.out)
            raw += rr
            styled += ss
            if hasattr(self.out, 'flush'):
                _, final_styled = await self.out.flush()
                if final_styled:
                    styled += final_styled
        return raw, styled

class ReverseStreamer:
    """Handles reverse streaming of text with styling and animations."""
    
    def __init__(self, utilities, terminal, text_processor, base_color='GREEN'):
        self.utils = utilities
        self.terminal = terminal
        self.text_processor = text_processor
        self._base_color = self.utils.get_base_color(base_color)

    async def reverse_stream(self, styled_text: str, preserved_msg: str = "", 
                           delay: float = 0.08):
        """Animate the reverse streaming of styled text."""
        # Split text into lines and process each line into styled words
        text_lines = styled_text.splitlines()
        processed_lines = []
        pattern_maps = {
            'by_name': self.utils.by_name,
            'start_map': self.utils.start_map,
            'end_map': self.utils.end_map
        }
        
        for line in text_lines:
            processed_lines.append(
                self.text_processor.split_into_styled_words(line, pattern_maps)
            )
            
        no_spacing = not bool(preserved_msg)
        
        # Animate reverse streaming
        for line_idx in range(len(processed_lines) - 1, -1, -1):
            while processed_lines[line_idx]:
                processed_lines[line_idx].pop()
                formatted = self.text_processor.format_styled_lines(
                    processed_lines,
                    self._base_color
                )
                await self.terminal.update_animated_display(
                    formatted, 
                    preserved_msg, 
                    no_spacing
                )
                await asyncio.sleep(delay)
                
        if preserved_msg:
            await self.reverse_stream_dots(preserved_msg)
            
        await self.terminal.update_animated_display()

    async def reverse_stream_dots(self, preserved_msg: str) -> str:
        """Animate the removal of dots from the preserved message."""
        msg_without_dots = preserved_msg.rstrip('.')
        num_dots = len(preserved_msg) - len(msg_without_dots)
        
        for i in range(num_dots - 1, -1, -1):
            await self.terminal.update_animated_display(
                "", 
                msg_without_dots + '.' * i
            )
            await asyncio.sleep(0.08)
            
        return msg_without_dots

class AnimationsManager:
    """Manages all animation-related functionality."""
    
    def __init__(self, utilities, terminal, text_processor):
        self.utils = utilities
        self.terminal = terminal
        self.text_processor = text_processor
    
    def create_dot_loader(self, prompt: str, output_handler=None, no_animation: bool = False):
        """Create a new dot loader animation instance."""
        return AsyncDotLoader(
            utilities=self.utils,
            prompt=prompt,
            adaptive_buffer=output_handler,
            output_handler=output_handler,
            no_animation=no_animation
        )
    
    def create_reverse_streamer(self, base_color='GREEN'):
        """Create a new reverse streamer animation instance."""
        return ReverseStreamer(
            utilities=self.utils,
            terminal=self.terminal,
            text_processor=self.text_processor,
            base_color=base_color
        )