# animations.py

import asyncio, json, time
from typing import Any, Tuple

class AsyncDotLoader:
    def __init__(self, styles, prompt: str="", output_handler=None, no_animation=False):
        self.styles = styles
        self.out = output_handler
        self.prompt = prompt.rstrip('.?!')
        self.no_anim = no_animation
        self.dot_char = '.' if prompt.endswith('.') or not prompt.endswith(('?','!')) else prompt[-1]
        self.dots = int(prompt.endswith(('.','?','!')))
        self.animation_complete = asyncio.Event()
        self.animation_task = None
        self.resolved = False
        self.terminal = None

    async def _animate(self) -> None:
        self.terminal._hide_cursor()
        try:
            while not self.animation_complete.is_set():
                await self.terminal.write_loading_state(self.prompt, self.dots, self.dot_char)
                await asyncio.sleep(0.4)
                if self.resolved and self.dots == 3:
                    await self.terminal.write_loading_state(self.prompt, 3, self.dot_char)
                    self.terminal._write('\n\n')
                    break
                self.dots = min(self.dots+1,3) if self.resolved else (self.dots+1)%4
            self.animation_complete.set()
        finally:
            self.terminal._show_cursor()

    async def run_with_loading(self, stream: Any) -> Tuple[str, str]:
        if not self.out: raise ValueError("output_handler must be provided")
        raw = styled = ""
        stored = []
        first_chunk = True
        if not self.no_anim:
            self.animation_task = asyncio.create_task(self._animate())
            await asyncio.sleep(0.01)
        try:
            # Handle both sync and async iterators
            if hasattr(stream, '__aiter__'):
                async for chunk in stream:
                    if not (c := chunk.strip()).startswith("data: ") or c=="data: [DONE]": 
                        continue
                    try:
                        if txt:=json.loads(c[6:])["choices"][0]["delta"].get("content",""):
                            if first_chunk:
                                self.resolved=True
                                if not self.no_anim: await self.animation_complete.wait()
                                first_chunk=False
                            if not self.animation_complete.is_set():
                                stored.append((txt,time.time()))
                            else:
                                if stored:
                                    stored.sort(key=lambda x: x[1])
                                    for i,(t,ts) in enumerate(stored):
                                        if i: await asyncio.sleep(ts-stored[i-1][1])
                                        r,s=await self.out.add(t,self.out)
                                        raw,styled=raw+r,styled+s
                                    stored.clear()
                                r2,s2=await self.out.add(txt,self.out)
                                raw,styled=raw+r2,styled+s2
                            await asyncio.sleep(0.01)
                    except json.JSONDecodeError:
                        pass
            else:
                for chunk in stream:  # Original sync iterator case
                    if not (c := chunk.strip()).startswith("data: ") or c=="data: [DONE]": 
                        continue
                    try:
                        if txt:=json.loads(c[6:])["choices"][0]["delta"].get("content",""):
                            if first_chunk:
                                self.resolved=True
                                if not self.no_anim: await self.animation_complete.wait()
                                first_chunk=False
                            if not self.animation_complete.is_set():
                                stored.append((txt,time.time()))
                            else:
                                if stored:
                                    stored.sort(key=lambda x: x[1])
                                    for i,(t,ts) in enumerate(stored):
                                        if i: await asyncio.sleep(ts-stored[i-1][1])
                                        r,s=await self.out.add(t,self.out)
                                        raw,styled=raw+r,styled+s
                                    stored.clear()
                                r2,s2=await self.out.add(txt,self.out)
                                raw,styled=raw+r2,styled+s2
                            await asyncio.sleep(0.01)
                    except json.JSONDecodeError:
                        pass
        finally:
            self.resolved=True
            self.animation_complete.set()
            if self.animation_task: await self.animation_task
            if stored:
                stored.sort(key=lambda x: x[1])
                for i,(t,ts) in enumerate(stored):
                    if i: await asyncio.sleep(ts-stored[i-1][1])
                    r,s=await self.out.add(t,self.out)
                    raw,styled=raw+r,styled+s
            r,s=await self.out.flush()
            if hasattr(self.out,'flush'):
                _,s2=await self.out.flush()
                s+=s2
            return raw+r, styled+s

class ReverseStreamer:
    def __init__(self, styles, terminal=None, base_color='GREEN'):
        self.styles = styles
        self.terminal = terminal
        self._base_color = self.styles.get_base_color(base_color)

    async def reverse_stream(self, styled_text: str, preserved_msg: str="", delay: float=0.08, preconversation_text: str=""):
        """Reverse stream text while preserving preconversation text."""
        if preconversation_text and styled_text.startswith(preconversation_text):
            conversation_text = styled_text[len(preconversation_text):].lstrip()
        else:
            conversation_text = styled_text
        lines = self._prepare_lines(conversation_text)
        no_spacing = not preserved_msg
        await self._reverse_stream_lines(lines, preserved_msg, no_spacing, delay, preconversation_text)
        await self._handle_punctuation(preserved_msg, delay)
        await self.terminal.update_animated_display(preconversation_text.rstrip()+"\n\n" if preconversation_text else "")

    def _prepare_lines(self, styled_text: str) -> list:
        lines = styled_text.splitlines()
        return [self.styles.split_into_styled_words(line) if line.strip() else [] for line in lines]

    async def _reverse_stream_lines(self, lines: list, preserved_msg: str, no_spacing: bool, delay: float, preconversation_text: str=""):
        for line_idx in range(len(lines)-1, -1, -1):
            while lines[line_idx]:
                lines[line_idx].pop()
                formatted_lines = self.styles.format_styled_lines(lines, self._base_color)
                full_display = (preconversation_text.rstrip()+"\n\n") if preconversation_text else ""
                if formatted_lines: full_display += formatted_lines
                await self.terminal.update_animated_display(full_display, preserved_msg, no_spacing)
                await asyncio.sleep(delay)

    async def _handle_punctuation(self, preserved_msg: str, delay: float):
        if not preserved_msg: return
        base = preserved_msg.rstrip('?.!')
        if preserved_msg.endswith(('!', '?')):
            await self._handle_exclamation_question(preserved_msg, base, delay)
        elif preserved_msg.endswith('.'):
            await self._handle_periods(base, delay)

    async def _handle_exclamation_question(self, preserved_msg: str, base: str, delay: float):
        char = preserved_msg[-1]
        count = len(preserved_msg) - len(base)
        for i in range(count,0,-1):
            await self.terminal.update_animated_display("", f"{base}{char*i}")
            await asyncio.sleep(delay)

    async def _handle_periods(self, base: str, delay: float):
        for i in range(3,0,-1):
            await self.terminal.update_animated_display("", f"{base}{'.'*i}")
            await asyncio.sleep(delay)

class Animations:
    def __init__(self, terminal, styles):
        self.terminal = terminal
        self.styles = styles

    def create_dot_loader(self, prompt: str, output_handler=None, no_animation=False):
        loader = AsyncDotLoader(self.styles, prompt, output_handler, no_animation)
        loader.terminal = self.terminal
        return loader
    
    def create_reverse_streamer(self, base_color='GREEN'):
        return ReverseStreamer(self.styles, self.terminal, base_color)