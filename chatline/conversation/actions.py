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
        self.is_silent = False  # UI-specific flag for message display
        self.prompt = ""        # UI-specific formatted prompt text
        self.last_user_input = ""

    def _get_system_prompt(self) -> str:
        """
        Retrieve the system prompt from the messages array.
        Returns empty string if no system message is found.
        """
        for msg in self.messages.messages:
            if msg.role == "system":
                return msg.content
        return ""

    def _get_last_user_input(self) -> str:
        """
        Retrieve the last user input from the messages array.
        Returns empty string if no user message is found.
        """
        for msg in reversed(self.messages.messages):
            if msg.role == "user":
                return msg.content
        return ""

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
        """
        Process a user message, generate a response, and store both in history.
        If silent=True, we do NOT append the user text to the displayed output,
        even if turn_number is > 1. That ensures repeated retries of a 'silent'
        message remain silent in the UI.
        """
        try:
            turn_number = self.history.current_state.turn_number + 1

            # 1) We always add the user message to the conversation so LLM sees "user" at each turn.
            self.messages.add_message("user", msg, turn_number)
            self.last_user_input = msg

            # Get system prompt from messages array
            sys_prompt = self._get_system_prompt()
            state_msgs = await self.messages.get_messages(sys_prompt)

            self.history.update_state(
                turn_number=turn_number,
                messages=state_msgs
            )

            # 2) If not silent, display the user prompt
            self.style.set_output_color('GREEN')
            prompt_text = "" if silent else f"> {msg}"
            loader = self.animations.create_dot_loader(
                prompt=prompt_text,
                no_animation=silent
            )

            # 3) Generate the LLM response
            msgs_for_generation = await self.messages.get_messages(sys_prompt)
            raw, styled = await loader.run_with_loading(self.generator(msgs_for_generation))

            # 4) Store the assistant's full reply
            if raw:
                self.messages.add_message("assistant", raw, turn_number)

                # Update conversation state again
                new_state_msgs = await self.messages.get_messages(sys_prompt)
                self.history.update_state(messages=new_state_msgs)

                # 5) Build final UI text:
                #    - If silent, skip the user text in the returned styled output.
                #    - If not silent, prepend user text to assistant text.
                if not silent:
                    # Format user text in final output
                    end_char = "..."
                    if msg.endswith(("?", "!")):
                        end_char = msg[-1] * 3
                    elif msg.endswith("."):
                        end_char = "..."
                    prompt_line = f"> {msg.rstrip('?.!')}{end_char}"
                    wrapped_prompt = self._wrap_terminal_style(prompt_line, self.terminal.width)
                    full_styled = f"{wrapped_prompt}\n\n{styled}"
                    return raw, full_styled
                else:
                    # Return only the assistant's text
                    return raw, styled

            return "", ""

        except Exception as e:
            self.logger.error(f"Message processing error: {e}", exc_info=True)
            return "", ""

    async def introduce_conversation(self, intro_msg: str) -> Tuple[str, str, str]:
        """
        Show any preface, then process the first user message silently (i.e. not displayed).
        We only display the assistant's reply in 'intro_styled'.
        """
        # 1) Preface panel
        styled_panel = await self.preface.format_content(self.style)
        styled_panel = self.style.append_single_blank_line(styled_panel)
        if styled_panel.strip():
            await self.terminal.update_display(styled_panel, preserve_cursor=True)

        # 2) The first user message is silent => user text is never shown
        raw, assistant_styled = await self._process_message(intro_msg, silent=True)

        # 3) Combine panel + assistant reply only (no user text) into 'intro_styled'
        full_styled = styled_panel + assistant_styled
        await self.terminal.update_display(full_styled)

        # 4) Update state and UI properties
        self.is_silent = True
        self.prompt = ""  # UI-specific prompt text
        self.history.update_state(
            preconversation_styled=styled_panel
        )
        return raw, full_styled, ""

    async def process_user_message(self, user_input: str, intro_styled: str) -> Tuple[str, str, str]:
        """
        Process a normal user message (non-silent).
        """
        scroller = self.animations.create_scroller()
        await scroller.scroll_up(intro_styled, f"> {user_input}", .5)

        raw, styled = await self._process_message(user_input, silent=False)
        self.is_silent = False
        self.prompt = self.terminal.format_prompt(user_input)  # UI-specific prompt text
        self.preface.clear()
        self.history.update_state(
            preconversation_styled=""
        )
        return raw, styled, self.prompt

    async def backtrack_conversation(self, intro_styled: str, is_retry: bool = False) -> Tuple[str, str, str]:
        """
        Return to the previous user message. If we are still in silent mode,
        we re-process that user message with silent=True => no user text shown.
        """
        current_turn = self.history.current_state.turn_number
        rev_streamer = self.animations.create_reverse_streamer()

        # Reverse only the text in 'intro_styled' (which never included the silent user message)
        await rev_streamer.reverse_stream(
            intro_styled,
            "",
            preconversation_text=self.preface.styled_content
        )

        # Find last user message in self.messages
        last_msg = next(
            (m.content for m in reversed(self.messages.messages)
             if m.role == "user"),
            None
        )
        if not last_msg:
            return "", intro_styled, ""

        # Remove the user+assistant pair
        user_idx = None
        for i in reversed(range(len(self.messages.messages))):
            if self.messages.messages[i].role == "user":
                user_idx = i
                break
        if user_idx is not None:
            # Ensure we don't remove the system message at index 0
            if user_idx > 0:
                # If next message is an assistant, remove both
                if (user_idx + 1 < len(self.messages.messages)
                    and self.messages.messages[user_idx + 1].role == "assistant"):
                    del self.messages.messages[user_idx:user_idx + 2]
                    self.history.restore_state(current_turn - 1)
                else:
                    del self.messages.messages[user_idx:user_idx + 1]
                    self.history.restore_state(current_turn - 1)

        # If we're still silent, re-process the message silently
        if self.is_silent:
            raw, styled = await self._process_message(last_msg, silent=True)
            # Return only the preface panel + assistant
            return raw, f"{self.preface.styled_content}\n{styled}", ""

        # Otherwise, normal backtrack for a non-silent message
        self.terminal.clear_screen()

        if is_retry:
            raw, styled = await self._process_message(last_msg, silent=False)
        else:
            new_input = await self.terminal.get_user_input(
                default_text=last_msg,
                add_newline=False
            )
            if not new_input:
                return "", intro_styled, ""
            self.terminal.clear_screen()
            raw, styled = await self._process_message(new_input, silent=False)
            last_msg = new_input

        self.prompt = self.terminal.format_prompt(last_msg)  # UI-specific prompt text
        return raw, styled, self.prompt

    async def _async_conversation_loop(self, system_msg: str, intro_msg: str):
        """
        Main async loop: system prompt + first user (silent),
        then repeatedly accept user input, or 'edit'/'retry' commands.
        """
        try:
            # Add the system message as the first message in the list
            self.messages.add_message("system", system_msg, 0)  # Turn 0 for system
            _, intro_styled, _ = await self.introduce_conversation(intro_msg)

            while True:
                user_input = await self.terminal.get_user_input()
                if not user_input:
                    continue
                cmd = user_input.lower().strip()
                if cmd in ["edit", "retry"]:
                    _, intro_styled, _ = await self.backtrack_conversation(
                        intro_styled, is_retry=(cmd == "retry")
                    )
                else:
                    _, intro_styled, _ = await self.process_user_message(
                        user_input, intro_styled
                    )

        except Exception as e:
            self.logger.error(f"Critical error: {e}", exc_info=True)
            raise
        finally:
            await self.terminal.update_display()

    def start_conversation(self, messages: dict) -> None:
        """
        Public entry: system + first user message. The first user message is silent in the UI,
        but still stored in the conversation for the LLM. Then normal conversation proceeds.
        """
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