# stream.py

from typing import Optional, Tuple, Protocol, Any, List, Dict, Callable, AsyncGenerator

# Local protocols to avoid circular imports
class Utilities(Protocol):
    def clear_screen(self) -> None: ...
    def write_and_flush(self, text: str) -> None: ...

class ComponentFactory(Protocol):
    @property
    def interface_manager(self) -> Any: ...
    @property
    def screen_manager(self) -> Any: ...
    def create_dot_loader(self, prompt: str, output_handler: Any = None, 
                         no_animation: bool = False) -> Any: ...
    def create_reverse_streamer(self) -> Any: ...

class ConversationState(Protocol):
    async def add_message(self, role: str, content: str) -> None: ...
    async def get_last_user_message(self) -> Optional[str]: ...
    async def mark_silent_message(self, is_silent: bool) -> None: ...
    async def set_preserved_prompt(self, prompt: str) -> None: ...
    async def get_conversation_messages(self) -> List[Dict[str, str]]: ...
    @property
    def is_last_message_silent(self) -> bool: ...
    @property
    def current_prompt(self) -> str: ...

class StreamHandler:
    def __init__(self, 
                 utilities: Utilities,
                 generator_func: Callable[[List[Dict[str, str]]], AsyncGenerator],
                 component_factory: ComponentFactory,
                 conversation_state: ConversationState):
        """
        Initialize StreamHandler with dependencies.
        
        Args:
            utilities: Utilities instance for terminal operations
            generator_func: Function that generates the response stream
            component_factory: Factory for creating UI components
            conversation_state: State manager for conversation
        """
        self.utils = utilities
        self.generator_func = generator_func
        self.factory = component_factory
        self.state = conversation_state

    async def get_input(self, default_text: str = "", add_newline: bool = True) -> str:
        """Get user input using the interface manager."""
        return await self.factory.interface_manager.get_user_input(
            default_text=default_text,
            add_newline=add_newline
        )

    async def stream_message(self, prompt_line: str, output_handler: Any = None) -> Tuple[str, str, str]:
        """Stream a message with loading animation."""
        loader = self.factory.create_dot_loader(prompt_line, output_handler)
        stream = self.generator_func(await self.state.get_conversation_messages())
        raw_text, styled_text = await loader.run_with_loading(stream)
        return raw_text, styled_text, f"{loader.prompt}{loader.dot_char * 3}"

    async def process_message(self, message: str, output_handler: Any, silent: bool = False) -> Tuple[str, str, str]:
        """Process a message and update conversation state."""
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
        """Handle retry request with reverse animation."""
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
        """Handle user message with scroll animation."""
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