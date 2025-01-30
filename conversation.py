# conversation.py

from typing import List, Dict, Any, Tuple
import logging
from dataclasses import dataclass

@dataclass
class Message:
    role: str
    content: str

class ConversationManager:
    def __init__(self, terminal, generator_func: Any, text_processor, 
                 animations_manager, system_prompt: str = None):
        self.terminal = terminal
        self.generator = generator_func
        self.text_processor = text_processor
        self.animations = animations_manager
        self.messages: List[Message] = []
        self.is_silent = False
        self.prompt = ""
        self.system_prompt = system_prompt or (
            'Be helpful, concise, and honest. Use text styles:\n'
            '- "quotes" for dialogue\n'
            '- [brackets] for observations\n'
            '- underscores for emphasis\n'
            '- asterisks for bold text'
        )

    async def get_messages(self) -> List[Dict[str, str]]:
        return ([{"role": "system", "content": self.system_prompt}] if self.system_prompt else []) + \
               [{"role": m.role, "content": m.content} for m in self.messages]

    async def _process_message(self, msg: str, silent=False) -> Tuple[str, str]:
        self.messages.append(Message("user", msg))
        handler = self.text_processor.create_styled_handler()
        
        raw, styled = await self.animations.create_dot_loader(
            prompt="" if silent else f"> {msg}",
            output_handler=handler,
            no_animation=silent
        ).run_with_loading(self.generator(await self.get_messages()))
        
        self.messages.append(Message("assistant", raw))
        return raw, styled

    async def handle_intro(self, intro_msg: str) -> Tuple[str, str, str]:
        raw, styled = await self._process_message(intro_msg, True)
        self.is_silent = True
        self.prompt = ""
        return raw, styled, ""

    async def handle_message(self, user_input: str, intro_styled: str) -> Tuple[str, str, str]:
        await self.terminal.handle_scroll(intro_styled, f"> {user_input}", 0.08)
        raw, styled = await self._process_message(user_input)
        self.is_silent = False
        self.prompt = f"> {user_input}..."
        return raw, styled, self.prompt

    async def handle_retry(self, intro_styled: str) -> Tuple[str, str, str]:
        await self.animations.create_reverse_streamer().reverse_stream(
            intro_styled,
            "" if self.is_silent else self.prompt
        )
        
        if self.is_silent:
            if last_user_msg := next((m.content for m in reversed(self.messages) 
                                    if m.role == "user"), None):
                raw, styled = await self._process_message(last_user_msg, True)
                return raw, styled, ""
        else:
            prev = next((m.content for m in reversed(self.messages) 
                        if m.role == "user"), None)
            if msg := await self.terminal.get_user_input(prev, False):
                await self.terminal.clear()
                raw, styled = await self._process_message(msg)
                self.prompt = f"> {msg}..."
                return raw, styled, self.prompt
                
        return "", "", ""

    async def run_conversation(self, system_msg: str = None, intro_msg: str = None):
        """Main conversation loop, moved from interface.py"""
        try:
            if system_msg is not None:
                self.system_prompt = system_msg
                
            await self.terminal.clear()
            _, intro_styled, _ = await self.handle_intro(
                intro_msg or "Introduce yourself in 3 lines, 7 words each..."
            )
            
            while True:
                if user := await self.terminal.get_user_input():
                    try:
                        _, intro_styled, _ = await self.handle_retry(intro_styled) if user.lower() == "retry" \
                            else await self.handle_message(user, intro_styled)
                    except Exception as e:
                        logging.error(f"Error processing message: {str(e)}", exc_info=True)
                        print(f"\nAn error occurred: {str(e)}")
        except KeyboardInterrupt:
            print("\nExiting...")
        except Exception as e:
            logging.error(f"Critical error: {str(e)}", exc_info=True)
            raise
        finally:
            await self.terminal.update_display()
            self.terminal._show_cursor()