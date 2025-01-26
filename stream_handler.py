# stream_handler.py
from typing import Optional, Tuple
from utilities import clear_screen, write_and_flush, manage_cursor
import logging

logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(levelname)s - %(message)s',
                   filename='chat_debug.log')

class StreamHandler:
    def __init__(self, generator_func, component_factory):
        self.generator_func = generator_func
        self.factory = component_factory
        self._last_message_silent = False
        self._preserved_prompt = ""
        logging.debug("StreamHandler initialized")

    async def get_input(self, default_text: str = "", add_newline: bool = True) -> str:
        logging.debug("Getting input")
        manage_cursor(True)
        if add_newline:
            write_and_flush("\n")
        from interface import get_user_input
        result = await get_user_input(default_text)
        manage_cursor(False)
        return result

    async def stream_message(self, conversation, prompt_line, output_handler=None) -> Tuple[str, str, str]:
        logging.debug("Streaming message")
        loader = self.factory.create_dot_loader(prompt_line, output_handler)
        stream = self.generator_func(conversation)
        raw_text, styled_text = await loader.run_with_loading(stream)
        return raw_text, styled_text, f"{loader.prompt}{loader.dot_char * 3}"

    async def process_message(self, conv_manager, message, output_handler, silent=False) -> Tuple[str, str, str]:
        logging.debug(f"Processing message (silent={silent})")
        if silent:
            loader = self.factory.create_dot_loader(
                "", output_handler=output_handler, no_animation=True
            )
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
        logging.debug("Handling retry")
        reverse_streamer = self.factory.create_reverse_streamer()
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
        logging.debug("Handling message")
        from interface import scroll_up
        scroll_up(intro_styled, f"> {user_input}", 0.08)
        conv_manager.add_message("user", user_input)
        return await self.process_message(conv_manager, user_input, output_handler)