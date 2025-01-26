# stream_handler.py

from typing import Optional, Tuple, Any
from conversation_state import ConversationState
from utilities import clear_screen, write_and_flush, manage_cursor

class StreamHandler:
    def __init__(self, generator_func, component_factory):
        self.generator_func = generator_func
        self.factory = component_factory
        self.state = ConversationState(
            system_prompt='Be helpful, concise, and honest. Use text styles:\n'
            '- "quotes" for dialogue\n'
            '- [brackets] for observations\n'
            '- _underscores_ for emphasis\n'
            '- *asterisks* for bold text'
        )

    async def get_input(self, default_text: str = "", add_newline: bool = True) -> str:
        return await self.factory.interface_manager.get_user_input(
            default_text=default_text,
            add_newline=add_newline
        )

    async def stream_message(self, prompt_line, output_handler=None) -> Tuple[str, str, str]:
        loader = self.factory.create_dot_loader(prompt_line, output_handler)
        stream = self.generator_func(await self.state.get_conversation_messages())
        raw_text, styled_text = await loader.run_with_loading(stream)
        return raw_text, styled_text, f"{loader.prompt}{loader.dot_char * 3}"

    async def process_message(self, message: str, output_handler: Any, silent: bool = False) -> Tuple[str, str, str]:
        if silent:
            loader = self.factory.create_dot_loader(
                "", output_handler=output_handler, no_animation=True
            )
            stream = self.generator_func(await self.state.get_conversation_messages())
            raw_text, styled_text = await loader.run_with_loading(stream)
            await self.state.add_message("assistant", raw_text)
            await self.state.mark_silent_message(True)
            await self.state.set_preserved_prompt("")
            return raw_text, styled_text, ""
        else:
            raw_text, styled_text, final_prompt = await self.stream_message(
                f"> {message}",
                output_handler
            )
            await self.state.add_message("assistant", raw_text)
            await self.state.mark_silent_message(False)
            await self.state.set_preserved_prompt(final_prompt)
            return raw_text, styled_text, final_prompt

    async def handle_retry(self, intro_styled: str, output_handler: Any, silent: bool = False) -> Tuple[str, str, str]:
        reverse_streamer = self.factory.create_reverse_streamer()
        preserved_msg = "" if silent else self.state.current_prompt
        
        await reverse_streamer.reverse_stream(intro_styled, preserved_msg)
        
        if silent:
            prev_message = await self.state.get_last_user_message()
            await self.state.add_message("user", prev_message)
            return await self.process_message(prev_message, output_handler, silent=True)
        else:
            prev_message = await self.state.get_last_user_message()
            final_message = await self.get_input(default_text=prev_message, add_newline=False)
            await self.factory.screen_manager.clear()
            await self.state.add_message("user", final_message)
            return await self.process_message(final_message, output_handler)

    async def handle_message(self, user_input: str, intro_styled: str, output_handler: Any) -> Tuple[str, str, str]:
        await self.factory.interface_manager.handle_scroll(
            intro_styled, 
            f"> {user_input}", 
            0.08
        )
        await self.state.add_message("user", user_input)
        return await self.process_message(user_input, output_handler)

    async def handle_intro(self, intro_msg: str, output_handler: Any) -> Tuple[str, str, str]:
        """Handle the initial introduction message."""
        await self.state.add_message("user", intro_msg)
        return await self.process_message(intro_msg, output_handler, silent=True)