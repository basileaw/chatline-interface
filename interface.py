import sys, time, asyncio, threading, json
from generator import generate_stream

def cs():
    if sys.stdout.isatty():
        sys.stdout.write("\033[2J\033[H")
        sys.stdout.flush()

def hc():
    if sys.stdout.isatty():
        sys.stdout.write("\033[?25l")
        sys.stdout.flush()

def sc():
    if sys.stdout.isatty():
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()

class DotLoader:
    def __init__(s, p, interval=0.4):
        # Punctuation logic:
        if p.endswith(("?", "!")):
            s.p, s.dc, s.dots = p[:-1], p[-1], 1
        elif p.endswith("."):
            s.p, s.dc, s.dots = p[:-1], ".", 1
        else:
            s.p, s.dc, s.dots = p, ".", 0

        s.i = interval
        s.resolved = False
        s.anim_done = threading.Event()
        s.stop_evt = threading.Event()
        s.th = None

    def _animate(self):
        hc()
        try:
            while not self.stop_evt.is_set():
                sys.stdout.write(f"\r{' '*80}\r{self.p}{self.dc*self.dots}")
                sys.stdout.flush()
                if self.resolved and self.dots == 3:
                    sys.stdout.write(f"\r{' '*80}\r{self.p}{self.dc*3}\n")
                    sys.stdout.flush()
                    self.anim_done.set()
                    break
                self.dots = min(self.dots + 1, 3) if self.resolved else (self.dots + 1) % 4
                time.sleep(self.i)
        finally:
            sc()

    async def run_with_loading(self, stream):
        acc = []
        first_chunk = True
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
                        if first_chunk:
                            self.resolved = True
                            first_chunk = False
                            while not self.anim_done.is_set():
                                await asyncio.sleep(0.05)
                            sys.stdout.write("\n")
                            sys.stdout.flush()
                        txt = data["choices"][0]["delta"].get("content", "")
                        acc.append(txt)
                        sys.stdout.write(txt)
                        sys.stdout.flush()
                    except json.JSONDecodeError:
                        pass
                await asyncio.sleep(0)
        finally:
            self.stop_evt.set()
            if self.th.is_alive():
                self.th.join()
        sys.stdout.write("\n")
        sys.stdout.flush()
        return "".join(acc)

async def stream_msg(conv, prompt_line):
    return await DotLoader(prompt_line).run_with_loading(generate_stream(conv))

def scroll_up(lines, prompt, delay=0.1):
    for i in range(len(lines)+1):
        cs()
        for ln in lines[i:]:
            print(ln)
        if i < len(lines):
            print()
        print(prompt, end="", flush=True)
        time.sleep(delay)

async def main():
    cs()
    conv = [
        {"role": "system", "content": "Be helpful, concise, and honest."},
        {"role": "user", "content": "Introduce yourself in 3 lines, 7 words each..."}
    ]
    intro = await stream_msg(conv, "Loading")
    conv.append({"role": "assistant", "content": intro})
    while True:
        sc()
        sys.stdout.write("\n> ")
        sys.stdout.flush()
        user = input().strip()
        hc()
        if not user:
            continue
        scroll_up(intro.splitlines(), f"> {user}", 0.08)
        conv.append({"role": "user", "content": user})
        reply = await stream_msg(conv, f"> {user}")
        conv.append({"role": "assistant", "content": reply})
        intro = reply

if __name__ == "__main__":
    asyncio.run(main())

