# conversation/actions.py

import logging
from typing import List, Tuple
import asyncio

class ConversationActions:
    """
    Handles the actions and flow of the conversation.
    """
    def __init__(self, display, stream, history, messages):
        self.display = display
        self.terminal = display.terminal      # Terminal operations
        self.io = display.io                  # Display I/O
        self.styles = display.styles          # Text styling
        self.animations = display.animations  # Animated effects
        self.stream = stream
        self.generator = stream.get_generator()  # Get the generator from stream

        self.history = history
        self.messages = messages
        self.logger = logging.getLogger(__name__)

        # Conversation-specific variables
        self.is_silent = False
        self.prompt = ""
        self.preconversation_text: List = []  # List to hold preface content
        self.preconversation_styled = ""
        self._display_strategies = {
            "text": self.styles.create_display_strategy("text"),
            "panel": self.styles.create_display_strategy("panel")
        }

    async def _process_message(self, msg: str, silent: bool = False) -> Tuple[str, str]:
        """
        Process a user message and generate a response.
        """
        try:
            turn_number = self.history.current_state.turn_number + 1

            # Add user message and update state.
            self.messages.add_message("user", msg, turn_number)
            state_msgs = await self.messages.get_messages(self.history.current_state.system_prompt)
            self.history.update_state(
                turn_number=turn_number,
                last_user_input=msg,
                messages=state_msgs
            )

            self.styles.set_output_color('GREEN')
            loader = self.animations.create_dot_loader(
                prompt="" if silent else f"> {msg}",
                no_animation=silent
            )

            msgs = await self.messages.get_messages(self.history.current_state.system_prompt)
            raw, styled = await loader.run_with_loading(self.generator(msgs))

            if raw:
                self.messages.add_message("assistant", raw, turn_number)
                state_msgs = await self.messages.get_messages(self.history.current_state.system_prompt)
                self.history.update_state(messages=state_msgs)

            return raw, styled
        except Exception as e:
            self.logger.error(f"Message processing error: {str(e)}", exc_info=True)
            return "", ""

    async def _process_preface(self, text_list: List) -> str:
        """
        Process a list of preface content items into styled text.
        """
        if not text_list:
            return ""
        styled_parts = []
        for content in text_list:
            formatted = await self._format_preface_content(content)
            styled_parts.append(formatted)
        return ''.join(styled_parts)

    async def _format_preface_content(self, content) -> str:
        """
        Format a single preface content item.
        The content is expected to have 'text', 'color', and 'display_type' attributes.
        """
        self.styles.set_output_color(content.color)
        strategy = self._display_strategies[content.display_type]
        _, styled = await self.styles.write_styled(strategy.format(content))
        return styled

    async def handle_intro(self, intro_msg: str) -> Tuple[str, str, str]:
        """
        Handle the initial conversation message.
        """
        self.preconversation_styled = await self._process_preface(self.preconversation_text)
        styled_panel = self.styles.append_single_blank_line(self.preconversation_styled)

        if styled_panel.strip():
            await self.io.update_display(styled_panel, preserve_cursor=True)

        raw, styled = await self._process_message(intro_msg, silent=True)
        full_styled = styled_panel + styled
        await self.io.update_display(full_styled)

        self.is_silent = True
        self.prompt = ""
        self.history.update_state(
            is_silent=True,
            prompt_display="",
            preconversation_styled=self.preconversation_styled
        )

        return raw, full_styled, ""

    async def handle_message(self, user_input: str, intro_styled: str) -> Tuple[str, str, str]:
        """
        Process a normal user message.
        """
        await self.io.handle_scroll(intro_styled, f"> {user_input}", 0.08)
        raw, styled = await self._process_message(user_input)

        self.is_silent = False
        end_char = user_input[-1] if user_input.endswith(('?', '!')) else '.'
        self.prompt = f"> {user_input.rstrip('?.!')}{end_char * 3}"
        self.preconversation_styled = ""

        self.history.update_state(
            is_silent=False,
            prompt_display=self.prompt,
            preconversation_styled=""
        )

        return raw, styled, self.prompt

    async def handle_edit_or_retry(self, intro_styled: str, is_retry: bool = False) -> Tuple[str, str, str]:
        """
        Handle edit or retry commands.
        """
        current_turn = self.history.current_state.turn_number

        rev_streamer = self.animations.create_reverse_streamer()
        await rev_streamer.reverse_stream(
            intro_styled,
            "" if self.is_silent else self.prompt,
            preconversation_text=self.preconversation_styled
        )

        last_msg = next((m.content for m in reversed(self.messages.messages) if m.role == "user"), None)
        if not last_msg:
            return "", intro_styled, ""

        if len(self.messages.messages) >= 2 and self.messages.messages[-2].role == "user":
            self.messages.remove_last_n_messages(2)
            self.history.restore_state(current_turn - 1)

        if self.is_silent:
            raw, styled = await self._process_message(last_msg, silent=True)
            self.history.update_state(
                is_silent=True,
                preconversation_styled=self.preconversation_styled
            )
            return raw, f"{self.preconversation_styled}\n{styled}", ""

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

        end_char = last_msg[-1] if last_msg.endswith(('?', '!')) else '.'
        self.prompt = f"> {last_msg.rstrip('?.!')}{end_char * 3}"
        self.history.update_state(prompt_display=self.prompt)
        return raw, styled, self.prompt

    async def run_conversation(self, system_msg: str, intro_msg: str):
        """
        Run the conversation loop starting with the given system and intro messages.
        """
        try:
            self.history.current_state.system_prompt = system_msg
            _, intro_styled, _ = await self.handle_intro(intro_msg)

            while True:
                user_input = await self.terminal.get_user_input()
                if not user_input:
                    continue

                cmd = user_input.lower().strip()
                if cmd in ["edit", "retry"]:
                    _, intro_styled, _ = await self.handle_edit_or_retry(
                        intro_styled,
                        is_retry=cmd == "retry"
                    )
                else:
                    _, intro_styled, _ = await self.handle_message(user_input, intro_styled)
        except Exception as e:
            self.logger.error(f"Critical error: {str(e)}", exc_info=True)
            raise
        finally:
            await self.io.update_display()

    def add_preface(self, text: str, color: str = None, display_type: str = "panel") -> None:
        """
        Add preface content to the conversation.
        To avoid cross-imports, a simple local PrefaceContent class is used.
        """
        class PrefaceContent:
            def __init__(self, text, color, display_type):
                self.text = text
                self.color = color
                self.display_type = display_type

        self.preconversation_text.append(PrefaceContent(text, color, display_type))
        self.history.update_state(preconversation_styled=self.preconversation_styled)
