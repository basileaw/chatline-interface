# interface.py
import sys
import asyncio
import time
from output_handler import OutputHandler, FORMATS
from generator import generate_stream

def clear_screen():
    if sys.stdout.isatty():
        sys.stdout.write("\033[2J\033[H")
        sys.stdout.flush()

def hide_cursor():
    if sys.stdout.isatty():
        sys.stdout.write("\033[?25l")
        sys.stdout.flush()

def show_cursor():
    if sys.stdout.isatty():
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()

def scroll_up(styled_lines, prompt, delay=0.1):
    lines = styled_lines.splitlines()
    for i in range(len(lines)+1):
        clear_screen()
        for ln in lines[i:]:
            sys.stdout.write(ln + '\n')
        if i < len(lines):
            sys.stdout.write('\n')
        sys.stdout.write(FORMATS['RESET'])  # Reset all formatting
        sys.stdout.write(prompt)
        sys.stdout.flush()
        time.sleep(delay)

class StreamHandler:
    def __init__(self, generator_func):
        self.generator_func = generator_func

    async def stream_message(self, conversation, prompt_line, output_handler=None):
        from dot_loader import DotLoader
        loader = DotLoader(prompt_line, output_handler=output_handler)
        stream = self.generator_func(conversation)
        return await loader.run_with_loading(stream)

async def main():
    clear_screen()
    output_handler = OutputHandler()
    stream_handler = StreamHandler(generate_stream)
    
    conv = [
        {"role": "system", "content": 'Be helpful, concise, and honest. Use text styles:\n- "quotes" for dialogue\n- [brackets] for observations\n- _underscores_ for emphasis'},
        {"role": "user", "content": "Introduce yourself in 3 lines, 7 words each..."}
    ]
    
    intro_raw, intro_styled = await stream_handler.stream_message(conv, "Loading", output_handler=output_handler)
    conv.append({"role": "assistant", "content": intro_raw})
    
    while True:
        show_cursor()
        sys.stdout.write("\n> ")
        sys.stdout.flush()
        user = input().strip()
        hide_cursor()
        
        if not user:
            continue
            
        scroll_up(intro_styled, f"> {user}", 0.08)
        conv.append({"role": "user", "content": user})
        reply_raw, reply_styled = await stream_handler.stream_message(conv, f"> {user}", output_handler=output_handler)
        conv.append({"role": "assistant", "content": reply_raw})
        intro_styled = reply_styled

if __name__ == "__main__":
    try:
        asyncio.run(main())
    finally:
        show_cursor()
        sys.stdout.write(FORMATS['RESET'])