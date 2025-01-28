import asyncio, json, time
from typing import Tuple, List, Protocol, Optional, Any

class Buffer(Protocol):
    async def add(self, chunk: str, output_handler: Any) -> Tuple[str, str]: ...
    async def flush(self, output_handler: Any) -> Tuple[str, str]: ...
    def reset(self) -> None: ...

class AsyncDotLoader:
    def __init__(self, utilities, prompt: str, adaptive_buffer: Optional[Buffer]=None,
                 interval=0.4, output_handler: Optional[Any]=None,
                 reuse_prompt=False, no_animation=False):
        self.utils, self.out, self.buffer = utilities, output_handler, adaptive_buffer
        self.interval, self.reuse, self.no_anim = interval, reuse_prompt, no_animation
        self.animation_task, self.animation_complete, self.resolved = None, asyncio.Event(), False
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
        finally:
            self.utils.show_cursor()

    async def _replay_chunks(self, stored: List[Tuple[str,float]]) -> Tuple[str,str]:
        if not stored: return "", ""
        stored.sort(key=lambda x: x[1])
        raw_acc, style_acc = "", ""
        for i, (txt, ts) in enumerate(stored):
            if i: await asyncio.sleep(ts - stored[i-1][1])
            raw, styled = await self.buffer.add(txt, self.out)
            raw_acc += raw; style_acc += styled
        return raw_acc, style_acc

    async def run_with_loading(self, stream: Any) -> Tuple[str, str]:
        if not self.buffer: raise ValueError("AdaptiveBuffer must be provided")
        raw, styled, stored, store_mode, first_chunk = "", "", [], True, True
        if not self.no_anim:
            self.animation_task = asyncio.create_task(self._animate())
            await asyncio.sleep(0.01)
        try:
            for chunk in stream:
                c = chunk.strip()
                if c == "data: [DONE]": break
                if c.startswith("data: "):
                    try:
                        data = json.loads(c[6:])
                        txt = data["choices"][0]["delta"].get("content","")
                        if txt:
                            if first_chunk:
                                self.resolved = True
                                if not self.no_anim: await self.animation_complete.wait()
                                first_chunk = False
                            now = time.time()
                            if store_mode:
                                if not self.animation_complete.is_set(): stored.append((txt, now))
                                else:
                                    store_mode = False
                                    r1, s1 = await self._replay_chunks(stored)
                                    raw += r1; styled += s1; stored.clear()
                                    r2, s2 = await self.buffer.add(txt, self.out)
                                    raw += r2; styled += s2
                            else:
                                r3, s3 = await self.buffer.add(txt, self.out)
                                raw += r3; styled += s3
                            await asyncio.sleep(0.01)
                    except json.JSONDecodeError:
                        pass
                await asyncio.sleep(0)
        finally:
            self.resolved = True
            self.animation_complete.set()
            if self.animation_task: await self.animation_task
            if store_mode:
                r4, s4 = await self._replay_chunks(stored)
                raw += r4; styled += s4
            rr, ss = await self.buffer.flush(self.out)
            raw += rr; styled += ss
            if hasattr(self.out, 'flush'):
                _, final_styled = await self.out.flush()
                if final_styled: styled += final_styled
        return raw, styled
