# interface.py
import sys
import asyncio
from helpers import clear_screen, show_cursor, hide_cursor, scroll_text
from stream_handler import StreamHandler
from generator import generate_stream

async def main():
    clear_screen()
    stream_handler = StreamHandler(generate_stream)
    
    conv = [
        {"role": "system", "content": "Be helpful, concise, and honest."},
        {"role": "user", "content": "Introduce yourself in 3 lines, 7 words each..."}
    ]
    
    intro = await stream_handler.stream_message(conv, "Loading")
    conv.append({"role": "assistant", "content": intro})
    
    while True:
        show_cursor()
        sys.stdout.write("\n> ")
        sys.stdout.flush()
        user = input().strip()
        hide_cursor()
        
        if not user:
            continue
            
        scroll_text(intro.splitlines(), f"> {user}", 0.08)
        conv.append({"role": "user", "content": user})
        reply = await stream_handler.stream_message(conv, f"> {user}")
        conv.append({"role": "assistant", "content": reply})
        intro = reply

if __name__ == "__main__":
    asyncio.run(main())