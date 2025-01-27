# state_managers/new_conversation_manager.py
from typing import List, Dict, Protocol, Optional, Any, Tuple
from dataclasses import dataclass

@dataclass
class Message:
    role: str
    content: str

class TerminalManager(Protocol):
    async def get_user_input(self, default_text: str = "", add_newline: bool = True) -> str: ...
    async def clear(self) -> None: ...
    async def handle_scroll(self, styled_lines: str, prompt: str, delay: float = 0.5) -> None: ...

class ComponentFactory(Protocol):
    def create_dot_loader(self, prompt: str, output_handler: Any = None, 
                         no_animation: bool = False) -> Any: ...
    def create_reverse_streamer(self) -> Any: ...
    def create_output_handler(self) -> Any: ...

class ConversationManager:
    def __init__(self, terminal_manager: TerminalManager, 
                 generator_func: Any, component_factory: ComponentFactory):
        self.terminal = terminal_manager
        self.generator = generator_func
        self.factory = component_factory
        self.messages: List[Message] = []
        self.is_last_message_silent = False
        self.preserved_prompt = ""
        self.system_prompt = (
            'Be helpful, concise, and honest. Use text styles:\n'
            '- "quotes" for dialogue\n'
            '- [brackets] for observations\n'
            '- _underscores_ for emphasis\n'
            '- *asterisks* for bold text'
        )

    async def get_conversation_messages(self) -> List[Dict[str, str]]:
        """Get all messages in the format expected by the API."""
        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.extend([{"role": msg.role, "content": msg.content} for msg in self.messages])
        return messages

    async def handle_intro(self, intro_msg: str) -> Tuple[str, str, str]:
        """Handle the initial introduction message."""
        self.messages.append(Message(role="user", content=intro_msg))
        output_handler = self.factory.create_output_handler()
        
        # Process in silent mode
        loader = self.factory.create_dot_loader(
            "",
            output_handler=output_handler,
            no_animation=True
        )
        stream = self.generator(await self.get_conversation_messages())
        raw_text, styled_text = await loader.run_with_loading(stream)
        
        self.messages.append(Message(role="assistant", content=raw_text))
        self.is_last_message_silent = True
        self.preserved_prompt = ""
        
        return raw_text, styled_text, ""

    async def handle_message(self, user_input: str, intro_styled: str) -> Tuple[str, str, str]:
        """Handle a regular user message."""
        output_handler = self.factory.create_output_handler()
        
        # Scroll previous content
        await self.terminal.handle_scroll(
            intro_styled,
            f"> {user_input}",
            0.08
        )
        
        self.messages.append(Message(role="user", content=user_input))
        loader = self.factory.create_dot_loader(
            f"> {user_input}",
            output_handler=output_handler
        )
        
        stream = self.generator(await self.get_conversation_messages())
        raw_text, styled_text = await loader.run_with_loading(stream)
        
        self.messages.append(Message(role="assistant", content=raw_text))
        self.is_last_message_silent = False
        final_prompt = f"> {user_input}..."
        self.preserved_prompt = final_prompt
        
        return raw_text, styled_text, final_prompt

    async def handle_retry(self, intro_styled: str) -> Tuple[str, str, str]:
        """Handle a retry request."""
        output_handler = self.factory.create_output_handler()
        reverse_streamer = self.factory.create_reverse_streamer()
        
        preserved_msg = "" if self.is_last_message_silent else self.preserved_prompt
        await reverse_streamer.reverse_stream(intro_styled, preserved_msg)
        
        if self.is_last_message_silent:
            # Get last user message and process silently
            for msg in reversed(self.messages):
                if msg.role == "user":
                    self.messages.append(Message(role="user", content=msg.content))
                    loader = self.factory.create_dot_loader(
                        "",
                        output_handler=output_handler,
                        no_animation=True
                    )
                    stream = self.generator(await self.get_conversation_messages())
                    raw_text, styled_text = await loader.run_with_loading(stream)
                    
                    self.messages.append(Message(role="assistant", content=raw_text))
                    return raw_text, styled_text, ""
                    break
        else:
            # Interactive retry
            prev_message = None
            for msg in reversed(self.messages):
                if msg.role == "user":
                    prev_message = msg.content
                    break
                    
            final_message = await self.terminal.get_user_input(
                default_text=prev_message,
                add_newline=False
            )
            
            await self.terminal.clear()
            self.messages.append(Message(role="user", content=final_message))
            
            loader = self.factory.create_dot_loader(
                f"> {final_message}",
                output_handler=output_handler
            )
            stream = self.generator(await self.get_conversation_messages())
            raw_text, styled_text = await loader.run_with_loading(stream)
            
            self.messages.append(Message(role="assistant", content=raw_text))
            final_prompt = f"> {final_message}..."
            self.preserved_prompt = final_prompt
            return raw_text, styled_text, final_prompt
            
        return "", "", ""