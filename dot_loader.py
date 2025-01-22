# dot_loader.py
import sys
import time
import threading
import asyncio
import json
from output_handler import FORMATS, OutputHandler, RawOutputHandler

def hide_cursor():
    if sys.stdout.isatty():
        sys.stdout.write("\033[?25l")
        sys.stdout.flush()

def show_cursor():
    if sys.stdout.isatty():
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()

class DotLoader:
    def __init__(self, prompt, interval=0.4, output_handler=None):
        # Punctuation logic
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
        self.output_handler = output_handler or RawOutputHandler()

    def _animate(self):
        hide_cursor()
        try:
            while not self.stop_evt.is_set():
                sys.stdout.write(f"\r{' '*80}\r{self.prompt}{self.dot_char*self.dots}")
                sys.stdout.flush()
                if self.resolved and self.dots == 3:
                    sys.stdout.write(f"\r{' '*80}\r{self.prompt}{self.dot_char*3}\n")
                    sys.stdout.flush()
                    self.anim_done.set()
                    break
                self.dots = min(self.dots + 1, 3) if self.resolved else (self.dots + 1) % 4
                time.sleep(self.interval)
        finally:
            show_cursor()

    async def run_with_loading(self, stream):
        accumulated = []
        first_chunk = True
        self.th = threading.Thread(target=self._animate, daemon=True)
        self.th.start()
        try:
            for chunk in stream:
                content = chunk.strip()
                if content == "data: [DONE]":
                    break
                if content.startswith("data: "):
                    try:
                        data = json.loads(content[6:])
                        if first_chunk:
                            self.resolved = True
                            first_chunk = False
                            while not self.anim_done.is_set():
                                await asyncio.sleep(0.05)
                            sys.stdout.write("\n")
                            sys.stdout.flush()
                        txt = data["choices"][0]["delta"].get("content", "")
                        raw_txt = self.output_handler.process_and_write(txt)
                        accumulated.append(raw_txt)
                    except json.JSONDecodeError:
                        pass
                await asyncio.sleep(0)
        finally:
            self.stop_evt.set()
            if self.th.is_alive():
                self.th.join()
            if isinstance(self.output_handler, OutputHandler):
                sys.stdout.write(FORMATS['RESET'])
            sys.stdout.write("\n")
            sys.stdout.flush()
        return "".join(accumulated)

