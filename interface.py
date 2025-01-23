import sys
import asyncio
import time
from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import FormattedText
from output_handler import OutputHandler, FORMATS
from generator import generate_stream
from reverse_stream import ReverseStreamer

# Initialize prompt session once
prompt_session = PromptSession()

# Initialize stream_handler at module level for proper cleanup
stream_handler = None

def clear_screen():
    if sys.stdout.isatty():
        sys.stdout.write("\033[2J\033[H")
        sys.stdout.flush()

async def get_user_input(default_text=""):
    """Wrapper for prompt_toolkit with non-editable prefix"""
    # Create prompt with non-editable prefix
    prompt = FormattedText([
        ('class:prompt', '> ')  # This part will be non-editable
    ])
    
    # Get input with optional default text
    result = await prompt_session.prompt_async(
        prompt,
        default=default_text,
    )
    
    return result.strip()

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

class ConversationManager:
    def __init__(self, system_prompt):
        self.conversation = [
            {"role": "system", "content": system_prompt}
        ]

    def add_user_message(self, content):
        self.conversation.append({"role": "user", "content": content})
        
    def add_assistant_message(self, content):
        self.conversation.append({"role": "assistant", "content": content})

    def get_last_user_message(self):
        """Get the most recent user message for retry functionality"""
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
        self._preserved_prompt = ""  # State variable for prompt preservation

    def show_cursor(self):
        """Show the terminal cursor"""
        if sys.stdout.isatty():
            sys.stdout.write("\033[?25h")
            sys.stdout.flush()

    def hide_cursor(self):
        """Hide the terminal cursor"""
        if sys.stdout.isatty():
            sys.stdout.write("\033[?25l")
            sys.stdout.flush()

    async def get_input(self, default_text="", add_newline=True):
        """Manage cursor visibility during input"""
        self.show_cursor()
        if add_newline:
            sys.stdout.write("\n")  # Add extra newline for spacing
        result = await get_user_input(default_text)
        self.hide_cursor()
        return result

    async def stream_message(self, conversation, prompt_line, output_handler=None):
        """Normal streaming with dot loader"""
        from dot_loader import DotLoader
        loader = DotLoader(prompt_line, output_handler=output_handler)
        stream = self.generator_func(conversation)
        raw_text, styled_text = await loader.run_with_loading(stream)
        final_prompt = f"{loader.prompt}{loader.dot_char * 3}"
        return raw_text, styled_text, final_prompt

    async def handle_retry(self, conv_manager, intro_styled, last_prompt, output_handler):
        """Handle retry command flow"""
        reverse_streamer = ReverseStreamer(output_handler, silent=False)
        await reverse_streamer.reverse_stream(intro_styled, self._preserved_prompt)
        
        prev_message = conv_manager.get_last_user_message()
        final_message = await self.get_input(default_text=prev_message, add_newline=False)
        
        clear_screen()
        conv_manager.add_user_message(final_message)
        self._last_message_silent = False  # Ensure we're in regular mode
        return await self.process_message(conv_manager, final_message, output_handler)

    async def handle_silent_retry(self, conv_manager, intro_styled, output_handler):
        """Handle silent retry flow"""
        reverse_streamer = ReverseStreamer(output_handler, silent=True)
        await reverse_streamer.reverse_stream(intro_styled, "")
        
        prev_message = conv_manager.get_last_user_message()
        conv_manager.add_user_message(prev_message)
        self._last_message_silent = True  # Ensure we stay in silent mode
        return await self.process_silent_message(conv_manager, prev_message, output_handler)

    async def handle_message(self, conv_manager, user_input, intro_styled, output_handler):
        """Handle regular message flow"""
        scroll_up(intro_styled, f"> {user_input}", 0.08)
        conv_manager.add_user_message(user_input)
        return await self.process_message(conv_manager, user_input, output_handler)

    async def process_message(self, conv_manager, message, output_handler):
        """Process message and return results"""
        reply_raw, reply_styled, reply_prompt = await self.stream_message(
            conv_manager.get_conversation(),
            f"> {message}",
            output_handler=output_handler
        )
        conv_manager.add_assistant_message(reply_raw)
        self._last_message_silent = False  # Explicitly set to False
        self._preserved_prompt = reply_prompt  # Save the prompt
        return reply_raw, reply_styled, reply_prompt

    async def process_silent_message(self, conv_manager, message, output_handler):
        """Process message with no visual feedback"""
        from dot_loader import DotLoader
        loader = DotLoader("", output_handler=output_handler, no_animation=True)
        stream = self.generator_func(conv_manager.get_conversation())
        raw_text, styled_text = await loader.run_with_loading(stream)
        conv_manager.add_assistant_message(raw_text)
        self._last_message_silent = True
        self._preserved_prompt = ""  # Clear the prompt for silent messages
        return raw_text, styled_text, ""

async def main():
    clear_screen()
    output_handler = OutputHandler()
    global stream_handler
    stream_handler = StreamHandler(generate_stream)
    
    conv_manager = ConversationManager(
        'Be helpful, concise, and honest. Use text styles:\n- "quotes" for dialogue\n- [brackets] for observations\n- _underscores_ for emphasis'
    )
    
    # Initial setup - using process_silent_message
    conv_manager.add_user_message("Introduce yourself in 3 lines, 7 words each...")
    _, intro_styled, _ = await stream_handler.process_silent_message(
        conv_manager, 
        "Introduce yourself in 3 lines, 7 words each...", 
        output_handler
    )
    
    while True:
        user = await stream_handler.get_input()
        if not user:
            continue
            
        if user.lower() == "retry":
            if stream_handler._last_message_silent:
                _, intro_styled, last_prompt = await stream_handler.handle_silent_retry(
                    conv_manager, intro_styled, output_handler
                )
            else:
                # Use the preserved prompt for regular retry
                _, intro_styled, last_prompt = await stream_handler.handle_retry(
                    conv_manager, intro_styled, stream_handler._preserved_prompt, output_handler
                )
        else:
            _, intro_styled, last_prompt = await stream_handler.handle_message(
                conv_manager, user, intro_styled, output_handler
            )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    finally:
        if stream_handler:
            stream_handler.show_cursor()  # Ensure cursor is visible on exit
            sys.stdout.write(FORMATS['RESET'])