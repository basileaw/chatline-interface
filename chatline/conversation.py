# conversation.py

import logging
from typing import List, Dict, Any, Tuple, Optional, Union, Callable, AsyncGenerator
from dataclasses import dataclass

@dataclass
class Message:
    role: str
    content: str

@dataclass
class PrefaceContent:
    text: str
    color: Optional[str]
    display_type: str = "text"

class Conversation:
    @staticmethod
    def get_default_messages() -> Tuple[str, str]:
        return (
            'Be helpful, concise, and honest. Use text styles:\n'
            '- "quotes" for dialogue\n'
            '- [brackets] for observations\n'
            '- underscores for emphasis\n'
            '- asterisks for bold text',
            "Introduce yourself in 3 lines, 7 words each..."
        )

    def __init__(self, 
                 terminal, 
                 generator_func: Union[Callable[[List[Dict[str, str]]], AsyncGenerator[str, None]], Any],
                 styles, 
                 animations_manager, 
                 system_prompt: str = None):
        self.terminal = terminal
        self.generator = generator_func
        self.styles = styles
        self.animations = animations_manager
        self.system_prompt = system_prompt
        self.messages: List[Message] = []
        self.is_silent = False
        self.prompt = ""
        self.preconversation_text: List[PrefaceContent] = []
        self.preconversation_styled = ""
        self._init_display_strategies()

    def _init_display_strategies(self) -> None:
        """Initialize display strategies at startup."""
        self._display_strategies = {
            "text": self.styles.create_display_strategy("text"),
            "panel": self.styles.create_display_strategy("panel")
        }

    async def get_messages(self) -> List[Dict[str, str]]:
        """Get all messages including system prompt."""
        base = [{"role": "system", "content": self.system_prompt}] if self.system_prompt else []
        return base + [{"role": m.role, "content": m.content} for m in self.messages]

    async def _process_preconversation_text(self, text_list: List[PrefaceContent]) -> str:
        """Process preconversation text with proper styling."""
        if not text_list: 
            return ""
            
        out = ""
        for content in text_list:
            self.styles.set_output_color(content.color)
            strat = self._display_strategies[content.display_type]
            formatted = strat.format(content)
            _, styled = await self.styles.write_styled(formatted)
            out += styled
        return out

    async def _process_message(self, msg: str, silent: bool = False) -> Tuple[str, str]:
        """Process a single message with proper error handling."""
        try:
            self.messages.append(Message("user", msg))
            self.styles.set_output_color('GREEN')
            
            loader = self.animations.create_dot_loader(
                prompt="" if silent else f"> {msg}",
                no_animation=silent
            )
            
            messages = await self.get_messages()
            raw, styled = await loader.run_with_loading(self.generator(messages))
            
            if raw:  # Only append assistant message if we got a valid response
                self.messages.append(Message("assistant", raw))
            return raw, styled
            
        except Exception as e:
            logging.error(f"Error processing message: {str(e)}", exc_info=True)
            return "", ""

    async def _get_last_user_message(self) -> Optional[str]:
        """Get the most recent user message."""
        return next((m.content for m in reversed(self.messages) if m.role == "user"), None)

    async def _remove_last_message_pair(self) -> None:
        """Remove the last user message and assistant response pair."""
        if len(self.messages) >= 2 and self.messages[-2].role == "user":
            self.messages.pop()  # Remove assistant's response
            self.messages.pop()  # Remove user's message

    async def handle_intro(self, 
                         intro_msg: str, 
                         preconversation_text: List[PrefaceContent] = None) -> Tuple[str, str, str]:
        """Handle the introduction sequence."""
        self.preconversation_styled = await self._process_preconversation_text(preconversation_text)
        panel_with_blank = self.styles.append_single_blank_line(self.preconversation_styled)
        
        if panel_with_blank.strip():
            await self.terminal.update_display(panel_with_blank, preserve_cursor=True)
            
        raw, styled = await self._process_message(intro_msg, silent=True)
        full_styled = panel_with_blank + styled
        await self.terminal.update_display(full_styled)
        
        self.is_silent = True
        self.prompt = ""
        return raw, full_styled, ""

    async def handle_message(self, 
                           user_input: str, 
                           intro_styled: str) -> Tuple[str, str, str]:
        """Handle a normal user message."""
        await self.terminal.handle_scroll(intro_styled, f"> {user_input}", 0.08)
        raw, styled = await self._process_message(user_input)
        
        self.is_silent = False
        end_char = '.' if not user_input.endswith(('?', '!')) else user_input[-1]
        self.prompt = f"> {user_input.rstrip('?.!')}{end_char * 3}"
        self.preconversation_styled = ""
        
        return raw, styled, self.prompt

    async def handle_edit_or_retry(self, 
                                 intro_styled: str, 
                                 is_retry: bool = False) -> Tuple[str, str, str]:
        """Handle edit or retry operations."""
        rev_streamer = self.animations.create_reverse_streamer()
        await rev_streamer.reverse_stream(
            intro_styled, 
            "" if self.is_silent else self.prompt,
            preconversation_text=self.preconversation_styled
        )
        
        last_msg = await self._get_last_user_message()
        if not last_msg:
            return "", intro_styled, ""
            
        await self._remove_last_message_pair()
        
        if self.is_silent:
            raw, styled = await self._process_message(last_msg, silent=True)
            full_styled = f"{self.preconversation_styled}\n{styled}"
            return raw, full_styled, ""
            
        if is_retry:
            await self.terminal.clear()
            raw, styled = await self._process_message(last_msg, silent=False)
            end_char = '.' if not last_msg.endswith(('?', '!')) else last_msg[-1]
            self.prompt = f"> {last_msg.rstrip('?.!')}{end_char * 3}"
            return raw, styled, self.prompt
        else:
            new_input = await self.terminal.get_user_input(default_text=last_msg, add_newline=False)
            if not new_input:
                return "", intro_styled, ""
            await self.terminal.clear()
            raw, styled = await self._process_message(new_input, silent=False)
            end_char = '.' if not new_input.endswith(('?', '!')) else new_input[-1]
            self.prompt = f"> {new_input.rstrip('?.!')}{end_char * 3}"
            return raw, styled, self.prompt

    async def handle_edit(self, intro_styled: str) -> Tuple[str, str, str]:
        """Handle edit operation."""
        return await self.handle_edit_or_retry(intro_styled, is_retry=False)

    async def handle_retry(self, intro_styled: str) -> Tuple[str, str, str]:
        """Handle retry operation."""
        return await self.handle_edit_or_retry(intro_styled, is_retry=True)

    def preface(self, text: str, color: Optional[str] = None, display_type: str = "panel") -> None:
        """Add preface content."""
        self.preconversation_text.append(PrefaceContent(text, color, display_type))

    def start(self, system_msg: str = None, intro_msg: str = None) -> None:
        """Start the conversation."""
        import asyncio
        asyncio.run(self._run_conversation(system_msg, intro_msg, self.preconversation_text))

    async def _run_conversation(self, 
                              system_msg: str = None, 
                              intro_msg: str = None,
                              preconversation_text: List[PrefaceContent] = None) -> None:
        """Main conversation loop."""
        try:
            if system_msg is None or intro_msg is None:
                system_msg, intro_msg = self.get_default_messages()
            
            self.system_prompt = system_msg
            _, intro_styled, _ = await self.handle_intro(intro_msg, preconversation_text)
            
            while True:
                user_input = await self.terminal.get_user_input()
                if not user_input: 
                    continue
                    
                try:
                    cmd = user_input.lower().strip()
                    if cmd == "edit":
                        _, intro_styled, _ = await self.handle_edit(intro_styled)
                    elif cmd == "retry":
                        _, intro_styled, _ = await self.handle_retry(intro_styled)
                    else:
                        _, intro_styled, _ = await self.handle_message(user_input, intro_styled)
                except Exception as e:
                    logging.error(f"Error processing message: {str(e)}", exc_info=True)
                    print(f"\nAn error occurred: {str(e)}")
                    
        except KeyboardInterrupt:
            print("\nExiting...")
        except Exception as e:
            logging.error(f"Critical error: {str(e)}", exc_info=True)
            raise
        finally:
            # Ensure display is cleaned up and cursor is visible on exit
            await self.terminal.update_display()
            self.terminal._show_cursor()