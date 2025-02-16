# conversation/actions.py

from typing import List, Tuple
import asyncio
import sys

class ConversationActions:
    """Manages conversation flow and actions."""
    def __init__(self, display, stream, history, messages, preface, logger):
        self.display = display
        self.terminal = display.terminal
        self.style = display.style
        self.animations = display.animations
        self.stream = stream
        self.generator = stream.get_generator()
        self.history = history
        self.messages = messages
        self.preface = preface
        self.logger = logger
        self.is_silent = False
        self.prompt = ""

    def _wrap_terminal_style(self, text: str, width: int) -> str:
        """
        Wrap text exactly as the terminal would, at fixed width boundaries.
        """
        if len(text) <= width:
            return text

        wrapped_chunks = []
        remaining_text = text
        while remaining_text:
            chunk = remaining_text[:width]
            wrapped_chunks.append(chunk)
            remaining_text = remaining_text[width:]
        return '\n'.join(wrapped_chunks)
    
    async def _process_message(self, msg: str, silent: bool = False) -> Tuple[str, str]:
        """Process a user message, generate a response, and store both in history."""
        try:
            turn_number = self.history.current_state.turn_number + 1

            # 1) Store the user's message as role="user"
            self.messages.add_message("user", msg, turn_number)

            sys_prompt = self.history.current_state.system_prompt
            state_msgs = await self.messages.get_messages(sys_prompt)

            self.history.update_state(
                turn_number=turn_number,
                last_user_input=msg,
                messages=state_msgs
            )

            self.style.set_output_color('GREEN')
            loader = self.animations.create_dot_loader(
                prompt="" if silent else f"> {msg}",
                no_animation=silent
            )

            # 2) Generate the streaming response
            msgs = await self.messages.get_messages(sys_prompt)
            raw, styled = await loader.run_with_loading(self.generator(msgs))

            # 3) <-- ADDED/CHANGED: store the assistant's full reply in conversation
            if raw:
                # Add assistant message to self.messages
                # If you prefer the styled text, you can store that. But usually raw is fine.
                self.messages.add_message("assistant", raw, turn_number)

                # Refresh the full conversation state
                new_state_msgs = await self.messages.get_messages(sys_prompt)
                self.history.update_state(
                    messages=new_state_msgs
                )

                # Optionally: also update 'last_user_input' or anything else if needed
                # e.g., self.history.update_state(last_assistant_reply=raw)

                if turn_number > 1:
                    # Format the prompt line with trailing punctuation
                    end_char = msg[-1] if msg.endswith(('?', '!')) else '.'
                    prompt_line = f"> {msg.rstrip('?.!')}{end_char * 3}"

                    # Apply terminal-style wrapping
                    wrapped_prompt = self._wrap_terminal_style(prompt_line, self.terminal.width)
                    full_styled = f"{wrapped_prompt}\n\n{styled}"
                    return raw, full_styled
                else:
                    return raw, styled

            return "", ""
        
        except Exception as e:
            self.logger.error(f"Message processing error: {e}", exc_info=True)
            return "", ""

    async def introduce_conversation(self, intro_msg: str) -> Tuple[str, str, str]:
        """Introduce conversation with preface content and initial message."""
        styled_panel = await self.preface.format_content(self.style)
        styled_panel = self.style.append_single_blank_line(styled_panel)

        if styled_panel.strip():
            await self.terminal.update_display(styled_panel, preserve_cursor=True)

        raw, styled = await self._process_message(intro_msg, silent=True)
        full_styled = styled_panel + styled
        await self.terminal.update_display(full_styled)

        self.is_silent = True
        self.prompt = ""
        self.history.update_state(
            is_silent=True,
            prompt_display="",
            preconversation_styled=styled_panel
        )
        return raw, full_styled, ""

    async def process_user_message(self, user_input: str, intro_styled: str) -> Tuple[str, str, str]:
        """Process a normal user message and generate a response."""
        scroller = self.animations.create_scroller()
        await scroller.scroll_up(intro_styled, f"> {user_input}", .5)

        raw, styled = await self._process_message(user_input)
        self.is_silent = False
        self.prompt = self.terminal.format_prompt(user_input)
        self.preface.clear()
        self.history.update_state(
            is_silent=False,
            prompt_display=self.prompt,
            preconversation_styled=""
        )
        return raw, styled, self.prompt

    async def backtrack_conversation(self, intro_styled: str, is_retry: bool = False) -> Tuple[str, str, str]:
        """Return to and modify the previous conversation exchange."""
        current_turn = self.history.current_state.turn_number
        rev_streamer = self.animations.create_reverse_streamer()

        await rev_streamer.reverse_stream(
            intro_styled,
            "",
            preconversation_text=self.preface.styled_content
        )

        last_msg = next((m.content for m in reversed(self.messages.messages) if m.role == "user"), None)
        if not last_msg:
            # No user messages found
            return "", intro_styled, ""

        # More robust removal: find last user and next assistant
        user_idx = None
        for i in reversed(range(len(self.messages.messages))):
            if self.messages.messages[i].role == "user":
                user_idx = i
                break
        if user_idx is not None:
            if (user_idx + 1 < len(self.messages.messages)
                and self.messages.messages[user_idx + 1].role == "assistant"):
                del self.messages.messages[user_idx:user_idx + 2]
                self.history.restore_state(current_turn - 1)
            else:
                del self.messages.messages[user_idx:user_idx + 1]
                self.history.restore_state(current_turn - 1)

        if self.is_silent:
            raw, styled = await self._process_message(last_msg, silent=True)
            self.history.update_state(
                is_silent=True,
                preconversation_styled=self.preface.styled_content
            )
            return raw, f"{self.preface.styled_content}\n{styled}", ""

        self.terminal.clear_screen()

        if is_retry:
            raw, styled = await self._process_message(last_msg)
        else:
            new_input = await self.terminal.get_user_input(
                default_text=last_msg,
                add_newline=False
            )
            if not new_input:
                return "", intro_styled, ""
            self.terminal.clear_screen()
            raw, styled = await self._process_message(new_input)
            last_msg = new_input

        self.prompt = self.terminal.format_prompt(last_msg)
        self.history.update_state(prompt_display=self.prompt)
        return raw, styled, self.prompt

    async def _async_conversation_loop(self, system_msg: str, intro_msg: str):
        """Asynchronous conversation loop."""
        try:
            self.history.current_state.system_prompt = system_msg
            _, intro_styled, _ = await self.introduce_conversation(intro_msg)

            while True:
                user_input = await self.terminal.get_user_input()
                if not user_input:
                    continue
                cmd = user_input.lower().strip()
                if cmd in ["edit", "retry"]:
                    _, intro_styled, _ = await self.backtrack_conversation(intro_styled, is_retry=(cmd == "retry"))
                else:
                    _, intro_styled, _ = await self.process_user_message(user_input, intro_styled)

        except Exception as e:
            self.logger.error(f"Critical error: {e}", exc_info=True)
            raise
        finally:
            await self.terminal.update_display()

    def start_conversation(self, messages: dict) -> None:
        """Public entry: start the conversation loop with error handling."""
        try:
            asyncio.run(self._async_conversation_loop(
                messages.get('system', ''),
                messages.get('user', '')
            ))
        except KeyboardInterrupt:
            self.logger.info("User interrupted")
            self.terminal.reset()
        except Exception as e:
            self.logger.error(f"Critical error in conversation: {e}", exc_info=True)
            self.terminal.reset()
            raise
        finally:
            self.terminal.reset()
