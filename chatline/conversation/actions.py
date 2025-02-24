# conversation/actions.py

from typing import List, Tuple, Dict, Any, Optional
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
        
        # UI-specific state, no longer stored in conversation state
        self.is_silent = False
        self.prompt = ""
        self.last_user_input = ""
        self.preconversation_styled = ""  # Stores the styled preface panel content
        
        # Track if we're in remote mode (for handling optional messages)
        self.is_remote_mode = hasattr(stream, 'endpoint')

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

    def _handle_state_update(self, new_state: Dict[str, Any]) -> None:
        """Handle state updates received from the backend."""
        if self.logger:
            self.logger.debug(f"Received state update from backend")
            if 'messages' in new_state and new_state['messages']:
                self.logger.debug(f"State contains {len(new_state['messages'])} messages")
        
        # If we sent no messages and got messages from the server, add them
        if (not self.messages.messages and 'messages' in new_state and 
            new_state['messages'] and len(new_state['messages']) > 0):
            
            self.logger.debug("Adding server-provided messages to conversation")
            for msg in new_state['messages']:
                # Ensure messages have a turn_number
                turn = msg.get('turn_number', 0) 
                self.messages.add_message(msg['role'], msg['content'], turn)
        
        # Update conversation state with the backend's response
        self.history.update_state(**new_state)

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

            # In remote mode with no existing messages, we might need to handle
            # server-provided initial messages differently
            first_interaction = len(self.messages.messages) == 0
            
            # Only add user message if we have a message or are not in remote mode
            if msg or not self.is_remote_mode:
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
            # Get current state for the backend
            current_state = self.history.create_state_snapshot()
            
            # Pass messages and state to generator with callback
            msgs_for_generation = await self.messages.get_messages(sys_prompt)
            
            # Log special case handling
            if first_interaction and self.is_remote_mode and not msg:
                self.logger.debug("First interaction with no messages. Server will provide defaults.")
            
            raw, styled = await loader.run_with_loading(
                self.generator(
                    messages=msgs_for_generation,
                    state=current_state,
                    state_callback=self._handle_state_update
                )
            )

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
                    if not msg:
                        # No user message to display
                        full_styled = styled
                    else:
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
        If in remote mode with no messages, the intro_msg can be empty.
        """
        # 1) Preface panel
        styled_panel = await self.preface.format_content(self.style)
        styled_panel = self.style.append_single_blank_line(styled_panel)
        if styled_panel.strip():
            await self.terminal.update_display(styled_panel, preserve_cursor=True)

        # 2) The first user message is silent => user text is never shown
        # In remote mode, intro_msg might be empty if server provides messages
        raw, assistant_styled = await self._process_message(intro_msg, silent=True)

        # 3) Combine panel + assistant reply only (no user text) into 'intro_styled'
        full_styled = styled_panel + assistant_styled
        await self.terminal.update_display(full_styled)

        # 4) Update UI-specific state
        self.is_silent = True
        self.prompt = ""
        self.preconversation_styled = styled_panel  # Store locally for animations
        return raw, full_styled, ""

    async def process_user_message(self, user_input: str, intro_styled: str) -> Tuple[str, str, str]:
        """
        Process a normal user message (non-silent).
        """
        scroller = self.animations.create_scroller()
        await scroller.scroll_up(intro_styled, f"> {user_input}", .5)

        raw, styled = await self._process_message(user_input, silent=False)
        self.is_silent = False
        self.prompt = self.terminal.format_prompt(user_input)
        self.preface.clear()
        self.preconversation_styled = ""  # Clear local preconversation content
        return raw, styled, self.prompt

    async def backtrack_conversation(self, intro_styled: str, is_retry: bool = False) -> Tuple[str, str, str]:
        """
        Return to the previous user message. If we are still in silent mode,
        we re-process that user message with silent=True => no user text shown.
        """
        current_turn = self.history.current_state.turn_number
        rev_streamer = self.animations.create_reverse_streamer()

        # Use the locally stored preconversation_styled for animations
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

        self.prompt = self.terminal.format_prompt(last_msg)
        return raw, styled, self.prompt

    async def _async_conversation_loop(self, system_msg: str, intro_msg: str):
        """
        Main async loop: system prompt + first user (silent),
        then repeatedly accept user input, or 'edit'/'retry' commands.
        
        In remote mode, system_msg and intro_msg can be empty if the server
        will provide default messages.
        """
        try:
            # Add the system message as the first message in the list if provided
            if system_msg:
                self.messages.add_message("system", system_msg, 0)  # Turn 0 for system
                
            # Process the first message (which might be empty in remote mode)
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
        
        In remote mode, messages can be empty and the server will provide defaults.
        """
        try:
            # Extract messages, allowing for empty strings in remote mode
            system_msg = messages.get('system', '')
            user_msg = messages.get('user', '')
            
            # Log message status
            if not system_msg and not user_msg and self.is_remote_mode:
                self.logger.debug("Starting conversation with no messages. Server will provide defaults.")
            
            asyncio.run(self._async_conversation_loop(system_msg, user_msg))
        except KeyboardInterrupt:
            self.logger.info("User interrupted")
            self.terminal.reset()
        except Exception as e:
            self.logger.error(f"Critical error in conversation: {e}", exc_info=True)
            self.terminal.reset()
            raise
        finally:
            self.terminal.reset()