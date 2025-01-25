import sys
import time
import threading
import asyncio
import json
from output_handler import OutputHandler, RawOutputHandler, FORMATS

def hide_cursor():
    if sys.stdout.isatty():
        sys.stdout.write("\033[?25l")
        sys.stdout.flush()

def show_cursor():
    if sys.stdout.isatty():
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()

class AdaptiveBuffer:
    def __init__(self, window_size=15):
        self.buf = []
        self.times = []
        self.wsize = window_size
        self.last_rel = time.time()
    
    def calc_interval(self):
        if len(self.times) < 2: return 0.08
        intervals = [t2 - t1 for t1, t2 in zip(self.times[-self.wsize:], self.times[-self.wsize+1:])]
        return 0.08 if not intervals else (sum(intervals)/len(intervals))*0.5

    async def add(self, chunk, out):
        now = time.time()
        self.buf.append(chunk)
        self.times.append(now)
        if len(self.times) > self.wsize*2:
            self.times = self.times[-self.wsize:]
        if len(self.buf) > self.wsize:
            return await self.release_some(out)
        return "", ""

    async def release_some(self, out):
        interval = self.calc_interval()
        raw_acc, style_acc = "", ""
        while self.buf and (time.time() - self.last_rel) >= interval:
            c = self.buf.pop(0)
            raw, styled = out.process_and_write(c)
            raw_acc += raw; style_acc += styled
            self.last_rel = time.time()
            await asyncio.sleep(0)
        return raw_acc, style_acc

    async def flush(self, out):
        r, s = "", ""
        while self.buf:
            rr, ss = await self.release_some(out)
            r += rr; s += ss
            if not self.buf:
                break
        return r, s

class DotLoader:
    def __init__(self, prompt, interval=0.4, output_handler=None, reuse_prompt=False, no_animation=False):
        if prompt.endswith(("?", "!")):
            self.prompt, self.dot_char, self.dots = prompt[:-1], prompt[-1], 1
        elif prompt.endswith("."):
            self.prompt, self.dot_char, self.dots = prompt[:-1], ".", 1
        else:
            self.prompt, self.dot_char, self.dots = prompt, ".", 0
        self.interval = interval
        self.resolved = False
        self.anim_done = threading.Event()
        self.stop_evt = threading.Event()
        self.th = None
        self.out = output_handler or RawOutputHandler()
        self.reuse = reuse_prompt
        self.no_anim = no_animation

    def _animate(self):
        hide_cursor()
        try:
            while not self.stop_evt.is_set():
                if self.reuse:
                    sys.stdout.write(f"\r{' '*80}\r{self.prompt}{self.dot_char*self.dots}")
                else:
                    sys.stdout.write(f"\r{' '*80}\r{self.prompt}{self.dot_char*self.dots}")
                sys.stdout.flush()

                if self.resolved and self.dots == 3:
                    if not self.reuse:
                        sys.stdout.write(f"\r{' '*80}\r{self.prompt}{self.dot_char*3}\n\n")
                    else:
                        sys.stdout.write(f"\r{' '*80}\r{self.prompt}{self.dot_char*3}\033[2B")
                    sys.stdout.flush()
                    time.sleep(self.interval)  # Add pause after final dots
                    self.anim_done.set()
                    break
                if self.resolved:
                    self.dots = min(self.dots + 1, 3)
                else:
                    self.dots = (self.dots + 1) % 4
                time.sleep(self.interval)
        except Exception:
            hide_cursor()
            raise

    async def _replay_chunks(self, stored, abuf):
        if not stored: return "", ""
        stored.sort(key=lambda x: x[1])
        r_acc, s_acc = "", ""
        for i, (txt, ts) in enumerate(stored):
            if i > 0:
                await asyncio.sleep(ts - stored[i-1][1])
            rr, ss = await abuf.add(txt, self.out)
            r_acc += rr; s_acc += ss
        return r_acc, s_acc

    async def run_with_loading(self, stream):
        raw, styled = "", ""
        abuf = AdaptiveBuffer()
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
                                # Wait for animation to complete before processing first chunk
                                if not self.no_anim:
                                    await asyncio.get_event_loop().run_in_executor(None, self.anim_done.wait)
                                first_chunk = False
                            
                            now = time.time()
                            if store_mode:
                                if not self.anim_done.is_set():
                                    stored.append((txt, now))
                                else:
                                    store_mode = False
                                    r1, s1 = await self._replay_chunks(stored, abuf)
                                    raw += r1; styled += s1
                                    stored.clear()
                                    r2, s2 = await abuf.add(txt, self.out)
                                    raw += r2; styled += s2
                            else:
                                r3, s3 = await abuf.add(txt, self.out)
                                raw += r3; styled += s3
                    except json.JSONDecodeError:
                        pass
                await asyncio.sleep(0)
        finally:
            self.stop_evt.set()
            if not self.no_anim and self.th and self.th.is_alive():
                self.th.join()
            if store_mode:
                r4, s4 = await self._replay_chunks(stored, abuf)
                raw += r4; styled += s4
            rr, ss = await abuf.flush(self.out)
            raw += rr; styled += ss

            # Get any remaining styled text from flush
            if hasattr(self.out, 'flush'):
                final_styled = self.out.flush()
                if final_styled:  # Add to our accumulated styled text
                    styled += final_styled

            # Reset style
            if isinstance(self.out, OutputHandler):
                sys.stdout.write(FORMATS['RESET'])
                sys.stdout.flush()

            sys.stdout.flush()

        return raw, styled