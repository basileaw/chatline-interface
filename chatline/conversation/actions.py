# conversation/actions.py

from typing import List, Tuple, Dict, Any
import asyncio
import sys
import termios
import tty
import os


class ConversationActions:
    """Manages conversation flow and actions."""

    def __init__(
        self,
        display,
        stream,
        history,
        messages,
        preface,
        logger,
        conclusion_string=None,
    ):
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
        self.conclusion_string = conclusion_string

        # UI-specific state
        self.is_silent = False
        self.prompt = ""
        self.last_user_input = ""
        self.preconversation_styled = ""
        self.conclusion_triggered = False

        # Local turn tracking (independent from conversation state)
        self.current_turn = 0
        self.history_index = -1

        # Detect remote vs. embedded mode (for generator usage)
        self.is_remote_mode = hasattr(stream, "endpoint")
        if self.is_remote_mode:
            self.logger.debug("Using remote mode for message generation")
        else:
            self.logger.debug("Using embedded mode for message generation")

    def _get_system_prompt(self) -> str:
        """Return the first system prompt found in our messages array, else empty."""
        for msg in self.messages.messages:
            if msg.role == "system":
                return msg.content
        return ""

    def _get_last_user_input(self) -> str:
        """Return the last user input from messages, else empty."""
        for msg in reversed(self.messages.messages):
            if msg.role == "user":
                return msg.content
        return ""

    def _handle_state_update(self, new_state: Dict[str, Any]) -> None:
        """Handle conversation state updates from a remote provider."""
        if self.logger:
            self.logger.debug("Received state update from backend")

        # CRITICAL FIX: Ensure messages from state are properly incorporated into local tracking
        if "messages" in new_state and new_state["messages"]:
            state_messages = new_state["messages"]
            current_messages = self.messages.messages

            # If we have fewer messages locally than in the state, update from state
            if len(state_messages) > len(current_messages):
                # Clear existing messages to avoid duplication
                self.messages.messages.clear()

                # Add messages from state with proper turn numbering
                turn = 0
                for msg in state_messages:
                    role = msg["role"]
                    content = msg["content"]

                    # System message is turn 0, user/assistant pairs share turn numbers
                    if role == "system":
                        self.messages.add_message(role, content, 0)
                    else:
                        # For user/assistant messages, increment turn for user messages
                        if role == "user":
                            turn += 1
                        self.messages.add_message(role, content, turn)

                # Update current turn counter
                self.current_turn = turn

                if self.logger:
                    self.logger.debug(
                        f"Updated internal message tracking from state: {len(state_messages)} messages"
                    )

        # Original code: Update the state in the history
        self.history.update_state(**new_state)

    def _wrap_terminal_style(self, text: str, width: int) -> str:
        """Hard-wrap text at a fixed width to match terminal output."""
        if len(text) <= width:
            return text

        wrapped_chunks = []
        remaining_text = text
        while remaining_text:
            chunk = remaining_text[:width]
            wrapped_chunks.append(chunk)
            remaining_text = remaining_text[width:]
        return "\n".join(wrapped_chunks)

    async def _process_message(self, msg: str, silent: bool = False) -> Tuple[str, str]:
        """
        Process a user message, generate a response, store both in history.
        If silent=True, we do NOT show the user text in the terminal output.
        """
        try:
            self.current_turn += 1

            # Add the user message
            self.messages.add_message("user", msg, self.current_turn)
            self.last_user_input = msg

            # Build the input to the LLM
            sys_prompt = self._get_system_prompt()
            state_msgs = await self.messages.get_messages(sys_prompt)
            self.history.update_state(messages=state_msgs)
            self.history_index = self.history.get_latest_state_index()

            # Output user text if not silent
            self.style.set_output_color("GREEN")
            prompt_text = "" if silent else f"> {msg}"
            loader = self.animations.create_dot_loader(
                prompt=prompt_text, no_animation=silent
            )

            # Prepare generator call
            current_state = self.history.create_state_snapshot()
            msgs_for_generation = await self.messages.get_messages(sys_prompt)

            if self.is_remote_mode:
                # Pass state to remote generator
                self.logger.debug("Calling remote generator with state and callback")
                raw, styled = await loader.run_with_loading(
                    self.generator(
                        messages=msgs_for_generation,
                        state=current_state,
                        state_callback=self._handle_state_update,
                    )
                )
            else:
                # Embedded mode
                self.logger.debug("Calling embedded generator with messages only")
                raw, styled = await loader.run_with_loading(
                    self.generator(messages=msgs_for_generation)
                )

            # Store assistant reply
            if raw:
                self.messages.add_message("assistant", raw, self.current_turn)

                new_state_msgs = await self.messages.get_messages(sys_prompt)
                self.history.update_state(messages=new_state_msgs)
                self.history_index = self.history.get_latest_state_index()

                # Check for conclusion string
                if self.conclusion_string:
                    if (
                        self.conclusion_string in raw
                        or self.conclusion_string in styled
                    ):
                        self.conclusion_triggered = True
                        self.terminal.hide_cursor()  # Ensure cursor is hidden
                        self.logger.debug(
                            f"Conclusion triggered: {self.conclusion_string}"
                        )

                # Build final UI text
                if not silent:
                    end_char = "..."
                    if msg.endswith(("?", "!")):
                        end_char = msg[-1] * 3
                    elif msg.endswith("."):
                        end_char = "..."
                    prompt_line = f"> {msg.rstrip('?.!')}{end_char}"
                    wrapped_prompt = self._wrap_terminal_style(
                        prompt_line, self.terminal.width
                    )
                    full_styled = f"{wrapped_prompt}\n\n{styled}"
                    return raw, full_styled
                else:
                    return raw, styled

            return "", ""

        except Exception as e:
            self.logger.error(f"Message processing error: {e}", exc_info=True)
            return "", ""

    async def introduce_conversation(self, intro_msg: str) -> Tuple[str, str, str]:
        """
        Show a preface panel (if any), then process the first user message silently.
        Returns (raw_assistant_reply, combined_styled_text, empty_string_for_prompt).
        """
        self.terminal.hide_cursor()

        styled_panel = await self.preface.format_content(self.style)
        styled_panel = self.style.append_single_blank_line(styled_panel)
        if styled_panel.strip():
            await self.terminal.update_display(styled_panel, preserve_cursor=False)

        # First user message is always silent => user text never shown
        raw, assistant_styled = await self._process_message(intro_msg, silent=True)
        full_styled = styled_panel + assistant_styled
        await self.terminal.update_display(full_styled)

        self.is_silent = True
        self.prompt = ""
        self.preconversation_styled = styled_panel
        self.terminal.hide_cursor()

        return raw, full_styled, ""

    async def process_user_message(
        self, user_input: str, intro_styled: str
    ) -> Tuple[str, str, str]:
        """
        Process a normal user message (visible in the terminal).
        """
        scroller = self.animations.create_scroller()
        await scroller.scroll_up(intro_styled, f"> {user_input}", 0.02)

        raw, styled = await self._process_message(user_input, silent=False)
        self.is_silent = False
        self.prompt = self.terminal.format_prompt(user_input)
        self.preface.clear()
        self.preconversation_styled = ""
        return raw, styled, self.prompt

    async def backtrack_conversation(
        self, intro_styled: str, is_retry: bool = False
    ) -> Tuple[str, str, str]:
        """
        Return to the previous user message, remove that user/assistant pair,
        then re-process or let the user edit it.
        """
        rev_streamer = self.animations.create_reverse_streamer()
        await rev_streamer.reverse_stream(
            intro_styled, "", preconversation_text=self.preface.styled_content
        )

        last_msg = next(
            (m.content for m in reversed(self.messages.messages) if m.role == "user"),
            None,
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
            # If next message is assistant, remove both
            if (
                user_idx + 1 < len(self.messages.messages)
                and self.messages.messages[user_idx + 1].role == "assistant"
            ):
                del self.messages.messages[user_idx : user_idx + 2]
                self.current_turn -= 1
                if self.history_index > 0:
                    self.history_index -= 1
                    self.history.restore_state_by_index(self.history_index)
            else:
                del self.messages.messages[user_idx : user_idx + 1]
                self.current_turn -= 1
                if self.history_index > 0:
                    self.history_index -= 1
                    self.history.restore_state_by_index(self.history_index)

        if self.is_silent:
            raw, styled = await self._process_message(last_msg, silent=True)
            return raw, f"{self.preface.styled_content}\n{styled}", ""

        self.terminal.clear_screen()
        if is_retry:
            raw, styled = await self._process_message(last_msg, silent=False)
        else:
            new_input = await self.terminal.get_user_input(
                default_text=last_msg, add_newline=False
            )
            if not new_input:
                return "", intro_styled, ""
            self.terminal.clear_screen()
            raw, styled = await self._process_message(new_input, silent=False)
            last_msg = new_input

        self.prompt = self.terminal.format_prompt(last_msg)
        return raw, styled, self.prompt

    def _read_line_raw_conclusion_mode(self) -> str:
        """
        Special raw input mode for conclusion state.
        No prompt, no cursor, no text input - only keyboard shortcuts.
        """
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            # Ensure cursor is hidden
            self.terminal.hide_cursor()

            # Switch to raw mode
            tty.setraw(fd, termios.TCSANOW)

            while True:
                c = os.read(fd, 1)

                # Only handle the allowed shortcuts
                if c == b"\x05":  # Ctrl+E
                    self.terminal.write("\r\n")
                    return "edit"
                elif c == b"\x12":  # Ctrl+R
                    self.terminal.write("\r\n")
                    return "retry"
                elif c == b"\x03":  # Ctrl+C
                    self.terminal.write("^C\r\n")
                    raise KeyboardInterrupt()
                elif c == b"\x04":  # Ctrl+D
                    self.terminal.write("\r\n")
                    return "exit"
                # Ignore all other input including Ctrl+P and regular characters

        finally:
            # Restore terminal settings
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            self.terminal.hide_cursor()

    async def _get_conclusion_mode_input(self) -> str:
        """Get input while in conclusion mode (no prompt, no cursor, only shortcuts)."""
        # Use the raw input method directly with hidden prompt
        result = await asyncio.get_event_loop().run_in_executor(
            None, self._read_line_raw_conclusion_mode
        )
        return result

    async def _async_conversation_loop(self, system_msg: str, intro_msg: str):
        """
        Main conversation loop:
         - Add system message (turn 0),
         - Process the first user message silently,
         - Then prompt for further input or let user edit.
        """
        try:
            # FIXED: Check if system message already exists before adding
            if system_msg:
                # Check if we already have a system message
                has_system = any(m.role == "system" for m in self.messages.messages)
                if not has_system:
                    self.messages.add_message("system", system_msg, 0)
                    sys_msgs = await self.messages.get_messages()
                    self.history.update_state(messages=sys_msgs)
                    self.history_index = self.history.get_latest_state_index()

            # Process the "intro" user message in silent mode
            _, intro_styled, _ = await self.introduce_conversation(intro_msg)

            # Now loop for interactive user input
            while True:
                if self.conclusion_triggered:
                    # Ensure cursor is hidden before entering conclusion mode
                    self.terminal.hide_cursor()
                    # Special handling for conclusion mode
                    user_input = await self._get_conclusion_mode_input()
                    if user_input in ["edit", "retry"]:
                        # Process backtracking
                        _, intro_styled, _ = await self.backtrack_conversation(
                            intro_styled, is_retry=(user_input == "retry")
                        )
                        self.conclusion_triggered = False  # Reset after edit/retry
                else:
                    # Normal input handling
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

    def start_conversation(self, messages: List[Dict[str, str]]) -> None:
        """
        Public entry from Interface.start(), with validated messages:
        - Possibly a system message at index 0
        - Multiple user/assistant pairs
        - Must end on user (unless empty)
        """
        try:
            # Reset local counters for a fresh start
            self.current_turn = 0
            self.history_index = -1

            # Handle the case of empty messages
            if not messages:
                # Just run the conversation loop with empty system and intro messages
                asyncio.run(self._async_conversation_loop("", ""))
                return

            # 1) Identify system_msg if present at messages[0]
            idx = 0
            system_msg = ""
            if messages[0]["role"] == "system":
                system_msg = messages[0]["content"]
                # CRITICAL FIX: Add system message immediately to self.messages
                self.messages.add_message("system", system_msg, 0)
                idx = 1

            # The final user message is always the last item
            final_user_msg = messages[-1]["content"]

            # 2) Insert all hidden pairs from messages[idx:-1]
            hidden_messages = messages[idx:-1]  # everything except the last user
            turn_count = 0

            i = 0
            while i < len(hidden_messages):
                if hidden_messages[i]["role"] == "user":
                    turn_count += 1
                    self.messages.add_message(
                        "user", hidden_messages[i]["content"], turn_count
                    )
                    i += 1
                    # If next is assistant, same turn_count
                    if (
                        i < len(hidden_messages)
                        and hidden_messages[i]["role"] == "assistant"
                    ):
                        self.messages.add_message(
                            "assistant", hidden_messages[i]["content"], turn_count
                        )
                        i += 1
                else:
                    # If for some reason the next message is "assistant" w/o a user,
                    # we can handle it or skip. But by prior validation, that shouldn't happen.
                    i += 1

            # Update our conversation state
            async def _update_history():
                sys_prompt = self._get_system_prompt()
                combined = await self.messages.get_messages(sys_prompt)
                self.history.update_state(messages=combined)
                self.history_index = self.history.get_latest_state_index()

            asyncio.run(_update_history())

            # 3) Run the normal async conversation loop with the final user message
            # CRITICAL FIX: Always pass empty string for system_msg to avoid duplication
            asyncio.run(self._async_conversation_loop("", final_user_msg))

        except KeyboardInterrupt:
            self.logger.info("User interrupted")
            self.terminal.reset()
        except Exception as e:
            self.logger.error(f"Critical error in conversation: {e}", exc_info=True)
            self.terminal.reset()
            raise
        finally:
            self.terminal.reset()
