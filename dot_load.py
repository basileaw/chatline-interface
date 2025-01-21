# dot_load.py
import threading
import time
import asyncio
import sys
import json
from typing import Callable, Generator, Any, AsyncGenerator, Union

class DotLoader:
    """A loading animation that displays animated dots/punctuation while awaiting streamed responses.
    
    Animation patterns:
    "Loading" -> Loading, Loading., Loading.., Loading...
    "Loading." -> Loading., Loading.., Loading..., Loading
    "Loading?" -> Loading?, Loading??, Loading???, Loading
    "Loading!" -> Loading!, Loading!!, Loading!!!, Loading
    """    
    def __init__(self, message: str = "Loading", interval: float = 0.75):
        if message.endswith(('?', '!')):
            self.message, self.dot_char, self.dots = message[:-1], message[-1], 1
        elif message.endswith('.'):
            self.message, self.dot_char, self.dots = message[:-1], '.', 1
        else:
            self.message, self.dot_char, self.dots = message, '.', 0
        self.interval = interval
        self.is_resolved = False
        self.animation_complete = threading.Event()
        self._stop_event = threading.Event()
        
    def _animate(self):
        """Handles animation loop with cursor control."""
        sys.stdout.write('\033[?25l')  # Hide cursor
        try:
            while not self._stop_event.is_set():
                sys.stdout.write(f'\r{" " * 80}\r{self.message}{self.dot_char * self.dots}')
                sys.stdout.flush()
                
                if self.is_resolved and self.dots == 3:
                    sys.stdout.write(f'\r{" " * 80}\r{self.message}{self.dot_char * 3}\n\n')
                    sys.stdout.flush()
                    self.animation_complete.set()
                    break
                    
                self.dots = min(self.dots + 1, 3) if self.is_resolved else (self.dots + 1) % 4
                time.sleep(self.interval)
        finally:
            sys.stdout.write('\033[?25h')  # Show cursor
            sys.stdout.flush()
        
    async def run_with_loading(self, stream_generator: Callable[..., Generator[str, None, None]] | 
                             Callable[..., AsyncGenerator[str, None]], *args, **kwargs) -> None:
        """Runs a streaming generator with loading animation until first chunk arrives."""
        try:
            self.animation_thread = threading.Thread(target=self._animate, daemon=True)
            self.animation_thread.start()
            first_chunk = True
            
            for chunk in stream_generator(*args, **kwargs):
                if chunk.startswith('data: '):
                    try:
                        data = json.loads(chunk.replace('data: ', '').strip())
                        if data == '[DONE]': break
                        if first_chunk:
                            self.is_resolved = True
                            while not self.animation_complete.is_set():
                                await asyncio.sleep(0.1)
                            first_chunk = False
                        sys.stdout.write(data['choices'][0]['delta']['content'])
                        sys.stdout.flush()
                    except json.JSONDecodeError:
                        continue
                await asyncio.sleep(0)
        finally:
            self._stop_event.set()
            if self.animation_thread and self.animation_thread.is_alive():
                self.animation_thread.join()

def create_demo_generator(delay: float = 5.0) -> Generator[str, None, None]:
    """Demo generator simulating a streaming response with delay."""
    time.sleep(delay)
    for chunk in ["Here's a computer joke:\n\n", 
                 "Why do programmers prefer dark mode?\n\n",
                 "Because light attracts bugs! 😄"]:
        yield f'data: {{"choices":[{{"delta":{{"content":"{chunk}"}}}}]}}\n\n'
        time.sleep(0.5)
    yield 'data: [DONE]\n\n'

if __name__ == "__main__":
    async def main():
        for i, msg in enumerate(["Loading", "Loading.", "Loading?", "Loading!"]):
            if i > 0: print("\n" + "="*50 + "\n")
            print(f"Testing with '{msg}':")
            await DotLoader(msg, interval=0.5).run_with_loading(create_demo_generator)
    asyncio.run(main())