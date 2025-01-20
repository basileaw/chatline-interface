import sys, time, asyncio
from typing import List

def clear_screen(): sys.stdout.write('\033[2J\033[H'); sys.stdout.flush()
def toggle_cursor(show=True): sys.stdout.write('\033[?25h' if show else '\033[?25l'); sys.stdout.flush()
def display_frame(content: str, delay: float = 0.05): clear_screen(); sys.stdout.write(content); sys.stdout.flush(); time.sleep(delay)

async def reverse_stream(demo_lines: List[str], response_lines: List[str], input_line: str, chunk_size: int = 2, delay: float = 0.05):
    """Reverse streams content using frame-based animation."""
    try:
        if not sys.stdout.isatty(): return
        toggle_cursor(False)
        
        text = ' '.join(response_lines)
        words = text.split()
        
        while words:
            words = words[:-chunk_size] if len(words) > chunk_size else []
            frame_content = demo_lines + [input_line, ""]
            if words:
                import textwrap
                frame_content.extend(textwrap.wrap(' '.join(words), width=70))
            display_frame('\n'.join(frame_content))
    finally:
        toggle_cursor(True)

def sync_reverse_stream(*args, **kwargs): return asyncio.run(reverse_stream(*args, **kwargs))

if __name__ == "__main__":
    demo_lines = [
        "Welcome to the reverse stream demo.",
        "Type 'exit' to quit, or 'retry' to reverse stream.",
        ""
    ]
    
    sample_response = (
        "I understand you're interested in the weather forecast. "
        "Currently, we're looking at sunny conditions with a high of 75°F. "
        "The humidity is relatively low at 45%, making it quite comfortable. "
        "As for tomorrow, we're expecting some changes with partly cloudy skies "
        "developing in the afternoon. There's a 30% chance of light showers in "
        "the evening, so you might want to keep an umbrella handy."
    )
    
    import textwrap
    response_lines = textwrap.wrap(sample_response, width=70)
    current_content = demo_lines.copy()
    last_message = None

    while True:
        clear_screen()
        print('\n'.join(current_content))
        
        toggle_cursor(True)
        user_input = input("> ")
        toggle_cursor(False)
        
        if user_input.lower() == 'exit': break
        
        input_line = f"> {user_input}"
        if user_input.lower() == 'retry' and last_message:
            sync_reverse_stream(demo_lines, response_lines, last_message)
            current_content = demo_lines.copy()
        else:
            current_content.extend([input_line, ""] + response_lines + [""])
            last_message = input_line