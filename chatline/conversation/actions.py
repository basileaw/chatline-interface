# conversation/actions.py

from typing import List, Tuple
import asyncio

class ConversationActions:
    """Manages conversation flow and actions."""
    def __init__(self, display, stream, history, messages, preface, logger):
        self.display = display
        self.terminal = display.terminal  # Terminal operations
        self.io = display.io              # Display I/O
        self.styles = display.styles      # Text styling
        self.animations = display.animations  # Animated effects
        self.stream = stream
        self.generator = stream.get_generator()  # Get the generator from stream
        self.history = history
        self.messages = messages
        self.preface = preface
        self.logger = logger

        self.is_silent = False
        self.prompt = ""
        self._display_strategies = {
            "text": self.styles.create_display_strategy("text"),
            "panel": self.styles.create_display_strategy("panel")
        }

    async def _process_message(self, msg: str, silent: bool = False) -> Tuple[str, str]:
        """Process a user message and generate a response."""
        try:
            turn_number = self.history.current_state.turn_number + 1
            self.messages.add_message("user", msg, turn_number)
            sys_prompt = self.history.current_state.system_prompt
            state_msgs = await self.messages.get_messages(sys_prompt)
            self.history.update_state(turn_number=turn_number,
                                    last_user_input=msg,
                                    messages=state_msgs)

            self.styles.set_output_color('GREEN')
            loader = self.animations.create_dot_loader(
                prompt="" if silent else f"> {msg}",
                no_animation=silent
            )
            msgs = await self.messages.get_messages(sys_prompt)
            raw, styled = await loader.run_with_loading(self.generator(msgs))

            if raw:
                self.messages.add_message("assistant", raw, turn_number)
                state_msgs = await self.messages.get_messages(sys_prompt)
                self.history.update_state(messages=state_msgs)

            return raw, styled
        except Exception as e:
            self.logger.error(f"Message processing error: {e}", exc_info=True)
            return "", ""

    async def introduce_conversation(self, intro_msg: str) -> Tuple[str, str, str]:
        """Introduce the conversation with preface content and initial message."""
        styled_panel = await self.preface.format_content(self.styles)
        styled_panel = self.styles.append_single_blank_line(styled_panel)

        if styled_panel.strip():
            await self.io.update_display(styled_panel, preserve_cursor=True)

        raw, styled = await self._process_message(intro_msg, silent=True)
        full_styled = styled_panel + styled
        await self.io.update_display(full_styled)

        self.is_silent = True
        self.prompt = ""
        self.history.update_state(is_silent=True,
                                prompt_display="",
                                preconversation_styled=styled_panel)
        return raw, full_styled, ""

    async def process_user_message(self, user_input: str, intro_styled: str) -> Tuple[str, str, str]:
        """Process a normal user message and generate a response."""
        scroller = self.animations.create_scroller()
        await scroller.scroll_styled(intro_styled, f"> {user_input}", 0.08)
        raw, styled = await self._process_message(user_input)
        self.is_silent = False
        self.prompt = self.io.format_prompt(user_input)
        self.preface.clear()
        self.history.update_state(is_silent=False,
                                prompt_display=self.prompt,
                                preconversation_styled="")
        return raw, styled, self.prompt

    async def backtrack_conversation(self, intro_styled: str, is_retry: bool = False) -> Tuple[str, str, str]:
        """Return to and modify the previous conversation exchange."""
        current_turn = self.history.current_state.turn_number
        rev_streamer = self.animations.create_reverse_streamer()
        await rev_streamer.reverse_stream(
            intro_styled,
            "" if self.is_silent else self.prompt,
            preconversation_text=self.preface.styled_content
        )

        last_msg = next((m.content for m in reversed(self.messages.messages) if m.role == "user"), None)
        if not last_msg:
            return "", intro_styled, ""

        if len(self.messages.messages) >= 2 and self.messages.messages[-2].role == "user":
            self.messages.remove_last_n_messages(2)
            self.history.restore_state(current_turn - 1)

        if self.is_silent:
            raw, styled = await self._process_message(last_msg, silent=True)
            self.history.update_state(is_silent=True,
                                    preconversation_styled=self.preface.styled_content)
            return raw, f"{self.preface.styled_content}\n{styled}", ""

        if is_retry:
            await self.io.clear()
            raw, styled = await self._process_message(last_msg)
        else:
            new_input = await self.terminal.get_user_input(default_text=last_msg, add_newline=False)
            if not new_input:
                return "", intro_styled, ""
            await self.io.clear()
            raw, styled = await self._process_message(new_input)
            last_msg = new_input

        self.prompt = self.io.format_prompt(last_msg)
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
            await self.io.update_display()

    def start_conversation(self, messages: dict) -> None:
        """Public entry: start the conversation loop with error handling."""
        try:
            asyncio.run(self._async_conversation_loop(
                messages.get('system', ''),
                messages.get('user', '')
            ))
        except KeyboardInterrupt:
            self.logger.info("User interrupted")
            self.display.terminal.reset()
        except Exception as e:
            self.logger.error(f"Critical error in conversation: {e}", exc_info=True)
            self.display.terminal.reset()
            raise
        finally:
            self.display.terminal.reset()