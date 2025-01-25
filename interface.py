# interface.py 

import sys
import asyncio
import time
import shutil
from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import FormattedText
from output_handler import OutputHandler
from generator import generate_stream
from reverse_stream import ReverseStreamer
from dot_loader import DotLoader
from painter import FORMATS

prompt_session = PromptSession()
stream_handler = None

def clear_screen():
    if sys.stdout.isatty():
        sys.stdout.write("\033[2J\033[H")
        sys.stdout.flush()

def split_into_display_lines(text, width):
    display_lines = []
    words = text.split()
    current_line = []
    current_length = 0
    
    for word in words:
        word_length = len(word) + (1 if current_length > 0 else 0)
        if current_length + word_length <= width:
            current_line.append(word)
            current_length += word_length
        else:
            if current_line:
                display_lines.append(' '.join(current_line))
            current_line = [word]
            current_length = len(word)
    
    if current_line:
        display_lines.append(' '.join(current_line))
    return display_lines

def get_visible_length(text):
    """Get visible length of text, ignoring ANSI escape codes"""
    in_escape = False
    visible_length = 0
    
    for char in text:
        if char == '\033':
            in_escape = True
        elif in_escape and char.isalpha():
            in_escape = False
        elif not in_escape:
            visible_length += 1
            
    return visible_length

def scroll_up(styled_lines, prompt, delay=0.5):
    term_width = shutil.get_terminal_size().columns
    paragraphs = styled_lines.split('\n')
    display_lines = []
    
    for paragraph in paragraphs:
        if not paragraph.strip():
            display_lines.append('')
            continue
            
        current_line = ''
        words = paragraph.split()
        
        for word in words:
            test_line = current_line + (' ' if current_line else '') + word
            if get_visible_length(test_line) <= term_width:
                current_line = test_line
            else:
                display_lines.append(current_line)
                current_line = word
                
        if current_line:
            display_lines.append(current_line)
    
    for i in range(len(display_lines) + 1):
        clear_screen()
        for ln in display_lines[i:]:
            sys.stdout.write(ln + '\n')
        sys.stdout.write(FORMATS['RESET'])
        sys.stdout.write(prompt)
        sys.stdout.flush()
        time.sleep(delay)

async def get_user_input(default_text=""):
    prompt = FormattedText([('class:prompt', '> ')])
    result = await prompt_session.prompt_async(prompt, default=default_text)
    return result.strip()

class ConversationManager:
    def __init__(self, system_prompt):
        self.conversation = [{"role": "system", "content": system_prompt}]

    def add_message(self, role, content):
        self.conversation.append({"role": role, "content": content})

    def get_last_user_message(self):
        for msg in reversed(self.conversation):
            if msg["role"] == "user":
                return msg["content"]
        return None

    def get_conversation(self):
        return self.conversation

class StreamHandler:
    def __init__(self, generator_func):
        self.generator_func = generator_func
        self._last_message_silent = False
        self._preserved_prompt = ""

    def _manage_cursor(self, show: bool):
        if sys.stdout.isatty():
            cmd = "\033[?25h" if show else "\033[?25l"
            sys.stdout.write(cmd)
            sys.stdout.flush()

    async def get_input(self, default_text="", add_newline=True):
        self._manage_cursor(True)
        if add_newline:
            sys.stdout.write("\n")
        result = await get_user_input(default_text)
        self._manage_cursor(False)
        return result

    async def stream_message(self, conversation, prompt_line, output_handler=None):
        loader = DotLoader(prompt_line, output_handler=output_handler)
        stream = self.generator_func(conversation)
        raw_text, styled_text = await loader.run_with_loading(stream)
        return raw_text, styled_text, f"{loader.prompt}{loader.dot_char * 3}"

    async def process_message(self, conv_manager, message, output_handler, silent=False):
        if silent:
            loader = DotLoader("", output_handler=output_handler, no_animation=True)
            stream = self.generator_func(conv_manager.get_conversation())
            raw_text, styled_text = await loader.run_with_loading(stream)
            conv_manager.add_message("assistant", raw_text)
            self._last_message_silent = True
            self._preserved_prompt = ""
            return raw_text, styled_text, ""
        else:
            raw_text, styled_text, final_prompt = await self.stream_message(
                conv_manager.get_conversation(),
                f"> {message}",
                output_handler
            )
            conv_manager.add_message("assistant", raw_text)
            self._last_message_silent = False
            self._preserved_prompt = final_prompt
            return raw_text, styled_text, final_prompt

    async def handle_retry(self, conv_manager, intro_styled, output_handler, silent=False):
        reverse_streamer = ReverseStreamer(output_handler)
        preserved_msg = "" if silent else self._preserved_prompt
        
        await reverse_streamer.reverse_stream(intro_styled, preserved_msg)
        
        if silent:
            prev_message = conv_manager.get_last_user_message()
            conv_manager.add_message("user", prev_message)
            return await self.process_message(conv_manager, prev_message, output_handler, silent=True)
        else:
            prev_message = conv_manager.get_last_user_message()
            final_message = await self.get_input(default_text=prev_message, add_newline=False)
            clear_screen()
            conv_manager.add_message("user", final_message)
            return await self.process_message(conv_manager, final_message, output_handler)

    async def handle_message(self, conv_manager, user_input, intro_styled, output_handler):
        scroll_up(intro_styled, f"> {user_input}", 0.08)
        conv_manager.add_message("user", user_input)
        return await self.process_message(conv_manager, user_input, output_handler)

async def main():
    clear_screen()
    output_handler = OutputHandler()
    global stream_handler
    stream_handler = StreamHandler(generate_stream)
    
    conv_manager = ConversationManager(
        'Be helpful, concise, and honest. Use text styles:\n'
        '- "quotes" for dialogue\n'
        '- [brackets] for observations\n'
        '- _underscores_ for emphasis\n'
        '- *asterisks* for bold text'
    )
    
    intro_msg = "Introduce yourself in 3 lines, 7 words each..."
    conv_manager.add_message("user", intro_msg)
    _, intro_styled, _ = await stream_handler.process_message(
        conv_manager, intro_msg, output_handler, silent=True
    )
    
    while True:
        try:
            user = await stream_handler.get_input()
            if not user:
                continue
                
            if user.lower() == "retry":
                _, intro_styled, _ = await stream_handler.handle_retry(
                    conv_manager, 
                    intro_styled, 
                    output_handler,
                    silent=stream_handler._last_message_silent
                )
            else:
                _, intro_styled, _ = await stream_handler.handle_message(
                    conv_manager, user, intro_styled, output_handler
                )
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"\nAn error occurred: {str(e)}")
            continue

if __name__ == "__main__":
    try:
        asyncio.run(main())
    finally:
        if stream_handler:
            stream_handler._manage_cursor(True)
            sys.stdout.write(FORMATS['RESET'])