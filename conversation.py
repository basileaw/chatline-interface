# conversation.py

import logging
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass

@dataclass
class Message:
    role: str
    content: str

class Conversation:
    @staticmethod
    def get_default_messages() -> Tuple[str, str]:
        """Get the default system and intro messages.
        
        Returns:
            Tuple[str, str]: (system_message, intro_message)
        """
        return (
            'Be helpful, concise, and honest. Use text styles:\n'
            '- "quotes" for dialogue\n'
            '- [brackets] for observations\n'
            '- underscores for emphasis\n'
            '- asterisks for bold text',
            "Introduce yourself in 3 lines, 7 words each..."
        )

    def __init__(self, terminal, generator_func: Any, styles, stream, 
                 animations_manager, system_prompt: str = None):
        self.terminal = terminal
        self.generator = generator_func
        self.styles = styles
        self.stream = stream
        self.animations = animations_manager
        self.messages: List[Message] = []
        self.is_silent = False
        self.prompt = ""
        self.system_prompt = system_prompt
        self.preconversation_styled = ""

    def _get_last_user_message(self) -> Optional[str]:
        """Helper method to find the last user message in the conversation."""
        return next((m.content for m in reversed(self.messages) if m.role == "user"), None)

    async def get_messages(self) -> List[Dict[str, str]]:
        return (
            [{"role": "system", "content": self.system_prompt}] if self.system_prompt else []
        ) + [
            {"role": m.role, "content": m.content}
            for m in self.messages
        ]

    async def _process_message(self, msg: str, silent=False) -> Tuple[str, str]:
        """Process a user message with the AI generator, returning (raw, styled)."""
        self.messages.append(Message("user", msg))
        
        # Set green color for AI responses
        self.stream.set_base_color('GREEN')
        
        raw, styled = await self.animations.create_dot_loader(
            prompt="" if silent else f"> {msg}",
            output_handler=self.stream,
            no_animation=silent
        ).run_with_loading(self.generator(await self.get_messages()))
        
        self.messages.append(Message("assistant", raw))
        return raw, styled

    async def _process_preconversation_text(self, text_list: List[Tuple[str, Optional[str]]]) -> str:
        """Process preconversation text with styling.
        
        Args:
            text_list: List of tuples (text, color) where text is the string to process
                       and color is an optional color name. Each text appears on its own line.
            
        Returns:
            str: Styled text output with an extra trailing newline for spacing.
        """
        if not text_list:
            return ""
            
        styled_output = ""
        for text, color in text_list:
            # Set color or reset to default for preconversation text
            self.stream.set_base_color(color)
            # Process the text with the stream
            raw, new_styled = await self.stream.add(text)
            styled_output += new_styled
            
        # Append one extra newline to separate from the next block of text
        return styled_output + "\n"

    async def handle_intro(self, intro_msg: str, preconversation_text: List[str] = None) -> Tuple[str, str, str]:
        """Process and display the intro message, showing preconversation text first if it exists."""
        # 1) Process preconversation text, which includes a trailing blank line
        self.preconversation_styled = await self._process_preconversation_text(preconversation_text)

        # 2) Immediately display the preconversation text (with blank line) if non-empty
        if self.preconversation_styled.strip():
            # Show only the preconversation text right now
            await self.terminal.update_display(self.preconversation_styled, preserve_cursor=True)

        # 3) Now process the AI intro text (silent streaming)
        raw, styled = await self._process_message(intro_msg, True)

        # 4) Combine them in memory for future scrolling or commands
        full_styled = self.preconversation_styled + styled

        self.is_silent = True
        self.prompt = ""
        
        return raw, full_styled, ""

    async def handle_message(self, user_input: str, intro_styled: str) -> Tuple[str, str, str]:
        """Handle a user's message, scrolling the stored intro and user input up the screen."""
        # Scroll everything (including the blank line from preconversation + the AI intro) 
        await self.terminal.handle_scroll(intro_styled, f"> {user_input}", 0.08)
        
        # Process the new message (with streaming if not silent)
        raw, styled = await self._process_message(user_input)
        self.is_silent = False
        
        # Reconstruct the prompt with proper punctuation
        end_char = '.' if not user_input.endswith(('?', '!')) else user_input[-1]
        self.prompt = f"> {user_input.rstrip('?.!')}{end_char * 3}"
        
        # Clear preconversation text after first user interaction
        self.preconversation_styled = ""
        
        # For future scrolls/animations, only show the new assistant reply
        full_styled = styled
        
        return raw, full_styled, self.prompt

    async def handle_edit_or_retry(self, intro_styled: str, is_retry: bool = False) -> Tuple[str, str, str]:
        """Handle both edit and retry commands using shared reverse streaming logic."""
        # Create reverse streamer with knowledge of preconversation text
        reverse_streamer = self.animations.create_reverse_streamer()
        await reverse_streamer.reverse_stream(
            intro_styled,
            "" if self.is_silent else self.prompt,
            preconversation_text=self.preconversation_styled
        )
        
        if self.is_silent:
            if last_msg := self._get_last_user_message():
                raw, styled = await self._process_message(last_msg, True)
                # Combine preconversation text with new styled response
                full_styled = self.preconversation_styled + styled
                return raw, full_styled, ""
        else:
            last_msg = self._get_last_user_message()
            if last_msg:
                if is_retry:
                    # For retry, immediately reprocess the last message
                    await self.terminal.clear()
                    raw, styled = await self._process_message(last_msg)
                    
                    # Apply same prompt reconstruction logic 
                    end_char = '.' if not last_msg.endswith(('?', '!')) else last_msg[-1]
                    self.prompt = f"> {last_msg.rstrip('?.!')}{end_char * 3}"
                    
                    # Combine preconversation text with new styled response
                    full_styled = self.preconversation_styled + styled
                    return raw, full_styled, self.prompt
                else:
                    # For edit, get user input with previous message pre-filled
                    if msg := await self.terminal.get_user_input(last_msg, False):
                        await self.terminal.clear()
                        raw, styled = await self._process_message(msg)
                        
                        # Prompt reconstruction
                        end_char = '.' if not msg.endswith(('?', '!')) else msg[-1]
                        self.prompt = f"> {msg.rstrip('?.!')}{end_char * 3}"
                        
                        # Combine preconversation text with new styled response
                        full_styled = self.preconversation_styled + styled
                        return raw, full_styled, self.prompt
                        
        return "", "", ""

    async def handle_edit(self, intro_styled: str) -> Tuple[str, str, str]:
        """Handle the edit command."""
        return await self.handle_edit_or_retry(intro_styled, is_retry=False)

    async def handle_retry(self, intro_styled: str) -> Tuple[str, str, str]:
        """Handle the retry command."""
        return await self.handle_edit_or_retry(intro_styled, is_retry=True)

    def run_conversation(self, system_msg: str = None, intro_msg: str = None,
                        preconversation_text: List[str] = None):
        """Synchronous entry point that handles asyncio setup
        
        Args:
            system_msg: Optional system message override
            intro_msg: Optional intro message override
            preconversation_text: Optional list of text to display before conversation
        """
        import asyncio
        asyncio.run(self._run_conversation(system_msg, intro_msg, preconversation_text))

    async def _run_conversation(self, system_msg: str = None, intro_msg: str = None,
                              preconversation_text: List[str] = None):
        """Internal async implementation of the conversation loop"""
        try:
            # If either message is None, use defaults for both
            if system_msg is None or intro_msg is None:
                system_msg, intro_msg = self.get_default_messages()
            
            self.system_prompt = system_msg
            _, intro_styled, _ = await self.handle_intro(intro_msg, preconversation_text)
            
            while True:
                if user := await self.terminal.get_user_input():
                    try:
                        if user.lower() == "edit":
                            _, intro_styled, _ = await self.handle_edit(intro_styled)
                        elif user.lower() == "retry":
                            _, intro_styled, _ = await self.handle_retry(intro_styled)
                        else:
                            _, intro_styled, _ = await self.handle_message(user, intro_styled)
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