# state/animations.py
import asyncio, json, time
from typing import Protocol, Optional, Any, Tuple, List

class Buffer(Protocol):
    async def add(self, chunk: str, output_handler: Any) -> Tuple[str, str]: ...
    async def flush(self, output_handler: Any) -> Tuple[str, str]: ...
    def reset(self) -> None: ...

class AsyncDotLoader:
    def __init__(self, utilities, prompt: str, adaptive_buffer: Optional[Buffer]=None,
                 interval=0.4, output_handler=None, reuse_prompt=False, no_animation=False):
        self.utils, self.out, self.buffer = utilities, output_handler, adaptive_buffer
        self.interval, self.reuse, self.no_anim = interval, reuse_prompt, no_animation
        self.animation_task, self.animation_complete = None, asyncio.Event()
        self.resolved = False
        suffix = prompt[-1] if prompt else ""
        if suffix in ("?", "!"): self.prompt, self.dot_char, self.dots = prompt[:-1], suffix, 1
        elif suffix == ".": self.prompt, self.dot_char, self.dots = prompt[:-1], ".", 1
        else: self.prompt, self.dot_char, self.dots = prompt, ".", 0

    async def _animate(self) -> None:
        self.utils.hide_cursor()
        try:
            self.utils.write_and_flush(f"\r{' '*80}\r{self.prompt}{self.dot_char*self.dots}")
            while not self.animation_complete.is_set():
                await asyncio.sleep(self.interval)
                if self.resolved and self.dots == 3:
                    seq = "\n\n" if not self.reuse else "\033[2B"
                    self.utils.write_and_flush(f"\r{' '*80}\r{self.prompt}{self.dot_char*3}{seq}")
                    self.animation_complete.set(); break
                self.dots = min(self.dots + 1, 3) if self.resolved else (self.dots + 1) % 4
                self.utils.write_and_flush(f"\r{' '*80}\r{self.prompt}{self.dot_char*self.dots}")
        finally: self.utils.show_cursor()

    async def run_with_loading(self, stream: Any) -> Tuple[str, str]:
        if not self.buffer: raise ValueError("AdaptiveBuffer must be provided")
        raw, styled, stored, first_chunk = "", "", [], True
        if not self.no_anim:
            self.animation_task = asyncio.create_task(self._animate())
            await asyncio.sleep(0.01)
        try:
            for chunk in stream:
                c = chunk.strip()
                if c == "data: [DONE]": break
                if c.startswith("data: "):
                    try:
                        txt = json.loads(c[6:])["choices"][0]["delta"].get("content","")
                        if txt:
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
            raw, styled = raw + r, styled + s
            if hasattr(self.out, 'flush'):
                _, final_styled = await self.out.flush()
                if final_styled: styled += final_styled
        return raw, styled

class ReverseStreamer:
    def __init__(self, utilities, terminal, text_processor, base_color='GREEN'):
        self.utils, self.terminal = utilities, terminal
        self.text_processor, self._base_color = text_processor, self.utils.get_base_color(base_color)

    async def reverse_stream(self, styled_text: str, preserved_msg: str = "", delay: float = 0.08):
        lines = [self.text_processor.split_into_styled_words(line, {
            'by_name': self.utils.by_name, 'start_map': self.utils.start_map, 
            'end_map': self.utils.end_map}) for line in styled_text.splitlines()]
        no_spacing = not bool(preserved_msg)
        for line_idx in range(len(lines) - 1, -1, -1):
            while lines[line_idx]:
                lines[line_idx].pop()
                await self.terminal.update_animated_display(
                    self.text_processor.format_styled_lines(lines, self._base_color),
                    preserved_msg, no_spacing)
                await asyncio.sleep(delay)
        if preserved_msg:
            msg_without_dots = preserved_msg.rstrip('.')
            for i in range(len(preserved_msg) - len(msg_without_dots) - 1, -1, -1):
                await self.terminal.update_animated_display("", msg_without_dots + '.' * i)
                await asyncio.sleep(0.08)
        await self.terminal.update_animated_display()

class AnimationsManager:
    def __init__(self, utilities, terminal, text_processor):
        self.utils, self.terminal, self.text_processor = utilities, terminal, text_processor
    
    def create_dot_loader(self, prompt: str, output_handler=None, no_animation: bool = False):
        return AsyncDotLoader(utilities=self.utils, prompt=prompt, adaptive_buffer=output_handler,
                            output_handler=output_handler, no_animation=no_animation)
    
    def create_reverse_streamer(self, base_color='GREEN'):
        return ReverseStreamer(utilities=self.utils, terminal=self.terminal,
                             text_processor=self.text_processor, base_color=base_color)