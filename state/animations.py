# state/animations.py
import asyncio, json, time
from typing import Protocol, Optional, Any, Tuple, List

class Buffer(Protocol):
    async def add(self, chunk: str, output_handler: Any) -> Tuple[str, str]: ...
    async def flush(self, output_handler: Any) -> Tuple[str, str]: ...
    def reset(self) -> None: ...

class AsyncDotLoader:
    def __init__(self, utilities, prompt: str, adaptive_buffer=None, output_handler=None, 
                 no_animation=False):
        self.utils = utilities
        self.out, self.buffer = output_handler, adaptive_buffer
        self.prompt, self.no_anim = prompt.rstrip('.?!'), no_animation
        self.dot_char = '.' if prompt.endswith('.') or not prompt.endswith(('?','!')) else prompt[-1]
        self.dots = 1 if prompt.endswith(('.','?','!')) else 0
        self.animation_complete = asyncio.Event()
        self.animation_task = None
        self.resolved = False

    async def _animate(self) -> None:
        self.terminal._hide_cursor()  # Use terminal's method directly
        try:
            while not self.animation_complete.is_set():
                await self.terminal.write_loading_state(self.prompt, self.dots)
                await asyncio.sleep(0.4)
                if self.resolved and self.dots == 3:
                    await self.terminal.write_loading_state(self.prompt, 3)
                    self.terminal._write('\n\n')  # Use terminal's method
                    break
                self.dots = min(self.dots + 1, 3) if self.resolved else (self.dots + 1) % 4
            self.animation_complete.set()
        finally:
            self.terminal._show_cursor()  # Use terminal's method

    async def run_with_loading(self, stream: Any) -> Tuple[str, str]:
        if not self.buffer: raise ValueError("AdaptiveBuffer must be provided")
        raw = styled = ""
        stored = []
        first_chunk = True
        if not self.no_anim:
            self.animation_task = asyncio.create_task(self._animate())
            await asyncio.sleep(0.01)
        try:
            for chunk in stream:
                if not (c := chunk.strip()).startswith("data: "): continue
                if c == "data: [DONE]": break
                try:
                    if txt := json.loads(c[6:])["choices"][0]["delta"].get("content",""):
                        if first_chunk:
                            self.resolved = True
                            if not self.no_anim: await self.animation_complete.wait()
                            first_chunk = False
                        if not self.animation_complete.is_set():
                            stored.append((txt, time.time()))
                        else:
                            if stored:
                                stored.sort(key=lambda x: x[1])
                                for i, (t, ts) in enumerate(stored):
                                    if i: await asyncio.sleep(ts - stored[i-1][1])
                                    r, s = await self.buffer.add(t, self.out)
                                    raw, styled = raw + r, styled + s
                                stored.clear()
                            r2, s2 = await self.buffer.add(txt, self.out)
                            raw, styled = raw + r2, styled + s2
                        await asyncio.sleep(0.01)
                except json.JSONDecodeError: pass
        finally:
            self.resolved = True
            self.animation_complete.set()
            if self.animation_task: await self.animation_task
            if stored:
                stored.sort(key=lambda x: x[1])
                for i, (t, ts) in enumerate(stored):
                    if i: await asyncio.sleep(ts - stored[i-1][1])
                    r, s = await self.buffer.add(t, self.out)
                    raw, styled = raw + r, styled + s
            r, s = await self.buffer.flush(self.out)
            if hasattr(self.out, 'flush'): _, s2 = await self.out.flush()
            return raw + r, styled + s + (s2 if hasattr(self.out, 'flush') else "")

class ReverseStreamer:
    def __init__(self, utilities, terminal, text_processor, base_color='GREEN'):
        self.utils = utilities
        self.terminal = terminal
        self.text_processor = text_processor
        self._base_color = text_processor.get_base_color(base_color)  # Use text_processor directly

    async def reverse_stream(self, styled_text: str, preserved_msg: str = "", delay: float = 0.08):
        lines = [self.text_processor.split_into_styled_words(line, 
                {'by_name': self.utils.by_name, 'start_map': self.utils.start_map, 
                 'end_map': self.utils.end_map}) for line in styled_text.splitlines()]
        no_spacing = not preserved_msg
        for line_idx in range(len(lines) - 1, -1, -1):
            while lines[line_idx]:
                lines[line_idx].pop()
                await self.terminal.update_animated_display(
                    self.text_processor.format_styled_lines(lines, self._base_color),
                    preserved_msg, no_spacing)
                await asyncio.sleep(delay)
        if preserved_msg:
            msg_base = preserved_msg.rstrip('.')
            num_dots = len(preserved_msg) - len(msg_base)
            for i in range(num_dots - 1, -1, -1):
                await self.terminal.update_animated_display("", msg_base + '.' * i)
                await asyncio.sleep(delay)
        await self.terminal.update_animated_display()

class AnimationsManager:
    def __init__(self, utilities, terminal, text_processor):
        self.utils = utilities
        self.terminal = terminal
        self.text_processor = text_processor
    
    def create_dot_loader(self, prompt: str, output_handler=None, no_animation=False):
        loader = AsyncDotLoader(self.utils, prompt, output_handler, output_handler, no_animation)
        loader.terminal = self.terminal  # Inject terminal dependency
        return loader
    
    def create_reverse_streamer(self, base_color='GREEN'):
        return ReverseStreamer(
            utilities=self.utils,
            terminal=self.terminal,
            text_processor=self.text_processor,
            base_color=base_color
        )