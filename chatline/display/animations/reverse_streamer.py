# display/animations/reverse_streamer.py
import asyncio
import re
from typing import List, Dict, Tuple


class ReverseStreamer:
    """Reverse-stream word-by-word animation preserving ANSI sequences."""

    def __init__(self, style, terminal, base_color="GREEN", logger=None):
        """Initialize with style engine, terminal, and base color."""
        self.style = style
        self.terminal = terminal
        self._base_color = self.style.get_base_color(base_color)
        self.logger = logger

    @staticmethod
    def tokenize_text(text: str) -> List[Dict[str, str]]:
        """Tokenize text into ANSI and character tokens."""
        ANSI_REGEX = re.compile(r"(\x1B\[[0-?]*[ -/]*[@-~])")
        tokens = []
        parts = re.split(ANSI_REGEX, text)
        for part in parts:
            if not part:
                continue
            if ANSI_REGEX.fullmatch(part):
                tokens.append({"type": "ansi", "value": part})
            else:
                for char in part:
                    tokens.append({"type": "char", "value": char})
        return tokens

    @staticmethod
    def reassemble_tokens(tokens: List[Dict[str, str]]) -> str:
        """Reassemble tokens into text."""
        return "".join(token["value"] for token in tokens)

    @staticmethod
    def group_tokens_by_word(
        tokens: List[Dict[str, str]],
    ) -> List[Tuple[str, List[Dict[str, str]]]]:
        """Group tokens into 'word' and 'space' groups."""
        groups = []
        current_group = []
        current_type = None  # 'word' or 'space'
        for token in tokens:
            if token["type"] == "ansi":
                if current_group:
                    current_group.append(token)
                else:
                    current_group = [token]
                    current_type = "word"
            else:
                if token["value"].isspace():
                    if current_group and current_type == "space":
                        current_group.append(token)
                    elif current_group and current_type == "word":
                        groups.append((current_type, current_group))
                        current_group = [token]
                        current_type = "space"
                    else:
                        current_group = [token]
                        current_type = "space"
                else:
                    if current_group and current_type == "word":
                        current_group.append(token)
                    elif current_group and current_type == "space":
                        groups.append((current_type, current_group))
                        current_group = [token]
                        current_type = "word"
                    else:
                        current_group = [token]
                        current_type = "word"
        if current_group:
            groups.append((current_type, current_group))
        return groups

    async def update_display(
        self,
        content: str,
        preserved_msg: str = "",
        no_spacing: bool = False,
        force_full_clear: bool = False,
    ) -> None:
        """Clear screen and update display with content and optional preserved message."""
        # Build full output content first
        output = ""
        if preserved_msg:
            output += preserved_msg
            if not no_spacing:
                output += "\n"

        if content:
            output += content

        # Check if content might exceed terminal height
        lines = output.split("\n") if output else []
        content_exceeds_height = len(lines) > (self.terminal.height - 1)

        # Always use full clear if content exceeds height or when explicitly requested
        if force_full_clear or content_exceeds_height:
            self.terminal.clear_screen()
            # Write the full content
            self.terminal.write(output)
        else:
            # Move cursor to home position for smaller content
            self.terminal.write("\033[H")
            # Write the full content
            self.terminal.write(output)
            # Clear from cursor to end of screen
            self.terminal.write("\033[J")

        # Reset formatting
        self.terminal.write(self.style.get_format("RESET"))

        # Ensure flush
        self.terminal.write("", newline=False)
        await self._yield()

    @staticmethod
    def extract_user_message(text: str) -> Tuple[str, str]:
        """
        Extract the user message (first line) from the full text.
        Returns a tuple of (user_message, remaining_text)
        """
        # Find the first line (user message)
        lines = text.split("\n", 2)

        if len(lines) <= 1:
            # If there's only one line, it's the user message
            return lines[0], ""
        elif len(lines) == 2:
            # If there are two lines, first is user message, second might be empty
            return lines[0], lines[1]
        else:
            # If there are 3+ lines, first is user message, rest is remaining content
            return lines[0], lines[1] + "\n" + lines[2]

    def _detect_bracketed_message(self, message: str) -> bool:
        """Detect if message contains a bracketed portion (even with external dots)."""
        # Strip prompt prefix if present
        text = message.strip()
        if text.startswith("> "):
            text = text[2:].strip()

        # Check for two cases:
        # 1. Fully enclosed brackets: [content]
        # 2. Brackets with external dots: [content]... or [content]!!! or [content]???
        if len(text) >= 2 and text.startswith("["):
            # Find the closing bracket
            bracket_end = text.find("]")
            if bracket_end != -1:
                # Check if everything after the bracket is just punctuation
                after_bracket = text[bracket_end + 1 :]
                is_all_punctuation = all(c in ".?!" for c in after_bracket)
                return bracket_end > 0 and is_all_punctuation

        return False

    def _parse_bracketed_message(self, message: str) -> Tuple[str, str, str]:
        """
        Parse bracketed message to extract components, handling external dots.

        Returns:
            Tuple of (prefix, bracket_content_without_brackets, animation_character)
        """
        # Extract prefix (like "> ")
        if message.startswith("> "):
            prefix = "> "
            text = message[2:].strip()
        else:
            prefix = ""
            text = message.strip()

        # Find the bracket content
        bracket_start = text.find("[")
        bracket_end = text.find("]")

        if bracket_start != -1 and bracket_end != -1 and bracket_end > bracket_start:
            # Extract content inside brackets
            inner_content = text[bracket_start + 1 : bracket_end]

            # Extract any punctuation after the closing bracket
            after_bracket = text[bracket_end + 1 :]

            # Determine animation character from external punctuation or default to '.'
            if after_bracket and after_bracket[0] in ".?!":
                animation_char = after_bracket[0]
            else:
                animation_char = "."

            return prefix, inner_content, animation_char

        # Fallback (shouldn't happen if detection worked correctly)
        return prefix, text, "."

    def _parse_bracketed_message_internal(self, message: str) -> Tuple[str, str, str]:
        """
        Parse bracketed message with internal dots format like "> [CONTINUE...]".

        Returns:
            Tuple of (prefix, bracket_content_with_dots, animation_character)
        """
        # Extract prefix (like "> ")
        if message.startswith("> "):
            prefix = "> "
            text = message[2:].strip()
        else:
            prefix = ""
            text = message.strip()

        # Remove the outer brackets to get content with dots
        if text.startswith("[") and text.endswith("]"):
            bracket_content_with_dots = text[1:-1]

            # Determine animation character - check what punctuation is at the end
            if bracket_content_with_dots and bracket_content_with_dots[-1] in ".?!":
                animation_char = bracket_content_with_dots[-1]
            else:
                animation_char = "."

            return prefix, bracket_content_with_dots, animation_char

        # Fallback
        return prefix, text, "."

    async def reverse_stream(
        self,
        styled_text: str,
        preserved_msg: str = "",
        delay: float = 0.08,
        preconversation_text: str = "",
        acceleration_factor: float = 1.15,
    ) -> None:
        """Animate reverse streaming of text word-by-word with acceleration."""
        # Extract the user message if preserved_msg is empty
        user_message = preserved_msg
        response_text = styled_text

        # If no preserved_msg was provided, extract the user message from the first line
        if not preserved_msg and styled_text:
            user_message, remaining_text = self.extract_user_message(styled_text)

            # If we successfully extracted a user message (starts with ">")
            if user_message.startswith(">"):
                # Use the user message as preserved_msg and the rest as the content to reverse stream
                response_text = remaining_text
            else:
                # No user message found, reset to original behavior
                user_message = ""

        # Process preconversation text if present
        if preconversation_text and response_text.startswith(preconversation_text):
            conversation_text = response_text[len(preconversation_text) :].lstrip()
        else:
            conversation_text = response_text

        # Tokenize and group the conversation text (not including user message)
        tokens = self.tokenize_text(conversation_text)
        groups = self.group_tokens_by_word(tokens)
        no_spacing = not user_message

        # If we have a user message, check if it's bracketed and needs conversion
        if user_message and self._detect_bracketed_message(user_message):
            # Convert external dots to internal dots for display during word removal
            prefix, bracket_content, animation_char = self._parse_bracketed_message(
                user_message
            )
            # Count external dots
            text = user_message.strip()
            if text.startswith("> "):
                text = text[2:].strip()
            bracket_end = text.find("]")
            if bracket_end != -1:
                after_bracket = text[bracket_end + 1 :]
                external_count = len(after_bracket)
                if external_count > 0:
                    # Convert to internal dots format for word removal display
                    user_message = (
                        f"{prefix}[{bracket_content}{animation_char * external_count}]"
                    )

        # Remove words until none remain
        chunks_to_remove = 1.0
        while any(group_type == "word" for group_type, _ in groups):
            chunks_this_round = round(chunks_to_remove)
            for _ in range(min(chunks_this_round, len(groups))):
                while groups and groups[-1][0] == "space":
                    groups.pop()
                if groups:
                    groups.pop()
            chunks_to_remove *= acceleration_factor
            remaining_tokens = []
            for _, grp in groups:
                remaining_tokens.extend(grp)
            new_text = self.reassemble_tokens(remaining_tokens)

            # Key fix: Ensure double newline between preconversation text and new response
            # for the first response retry scenario (when no user_message)
            if preconversation_text:
                if not user_message:  # First response retry case
                    full_display = preconversation_text.rstrip() + "\n\n" + new_text
                else:  # Normal retry case
                    full_display = preconversation_text + new_text
            else:
                full_display = new_text

            await self.update_display(full_display, user_message, no_spacing)
            await asyncio.sleep(delay)

        # Once all response words are removed, handle punctuation in the user message
        if user_message:
            await self._handle_punctuation(user_message, delay)
            return

        # Only reaches here if there's no user message (first response retry)
        # Ensure we preserve the double newline after preconversation text
        final_text = (
            preconversation_text.rstrip() + "\n\n" if preconversation_text else ""
        )
        await self.update_display(final_text)

    async def _handle_punctuation(self, preserved_msg: str, delay: float) -> None:
        """Animate punctuation in the preserved message, handling bracketed messages."""
        if not preserved_msg:
            return

        # Check if this is a bracketed message
        if self._detect_bracketed_message(preserved_msg):
            await self._handle_bracketed_punctuation(preserved_msg, delay)
        else:
            await self._handle_regular_punctuation(preserved_msg, delay)

    async def _handle_bracketed_punctuation(
        self, preserved_msg: str, delay: float
    ) -> None:
        """Handle punctuation removal for bracketed messages with internal dots."""
        # Parse the message - now expecting internal dots format like "> [CONTINUE...]"
        prefix, bracket_content_with_dots, animation_char = (
            self._parse_bracketed_message_internal(preserved_msg)
        )

        # Remove animation characters from the end of bracket content
        base_content = bracket_content_with_dots.rstrip(animation_char)
        dot_count = len(bracket_content_with_dots) - len(base_content)

        if dot_count > 0:
            # Animate removing dots from inside brackets
            for i in range(dot_count, 0, -1):
                display_text = f"{prefix}[{base_content}{animation_char * i}]"
                await self.update_display("", display_text, force_full_clear=True)
                await asyncio.sleep(delay)

        # Show the final state without animation characters
        final_text = f"{prefix}[{base_content}]"
        await self.update_display("", final_text, force_full_clear=True)

    async def _handle_regular_punctuation(
        self, preserved_msg: str, delay: float
    ) -> None:
        """Handle punctuation removal for regular messages (original behavior)."""
        base = preserved_msg.rstrip("?.!")
        if preserved_msg.endswith(("!", "?")):
            char = preserved_msg[-1]
            count = len(preserved_msg) - len(base)
            for i in range(count, 0, -1):
                await self.update_display(
                    "", f"{base}{char * i}", force_full_clear=True
                )
                await asyncio.sleep(delay)
            # Show the message without punctuation as the final state
            await self.update_display("", base, force_full_clear=True)
        elif preserved_msg.endswith("."):
            for i in range(3, 0, -1):
                await self.update_display("", f"{base}{'.' * i}", force_full_clear=True)
                await asyncio.sleep(delay)
            # Show the message without punctuation as the final state
            await self.update_display("", base, force_full_clear=True)

    async def reverse_stream_multiple_exchanges(
        self,
        styled_text: str,
        exchanges_to_remove: int = 1,
        delay: float = 0.08,
        preconversation_text: str = "",
        acceleration_factor: float = 1.15,
    ) -> None:
        """
        Reverse stream multiple exchanges from the conversation.

        Args:
            styled_text: The full conversation text to process
            exchanges_to_remove: Number of user/assistant exchanges to remove
            delay: Base delay between animations
            preconversation_text: Text to preserve at the top
            acceleration_factor: How much to accelerate the animation
        """
        # Split the text into lines to identify exchanges
        lines = styled_text.split("\n")

        # Find user message lines (they start with ">")
        user_line_indices = []
        for i, line in enumerate(lines):
            if line.strip().startswith(">"):
                user_line_indices.append(i)

        # If we don't have enough exchanges to remove, fall back to regular reverse stream
        if len(user_line_indices) < exchanges_to_remove:
            await self.reverse_stream(
                styled_text,
                delay=delay,
                preconversation_text=preconversation_text,
                acceleration_factor=acceleration_factor,
            )
            return

        # Calculate which exchanges to remove
        exchanges_to_keep = len(user_line_indices) - exchanges_to_remove

        if exchanges_to_keep <= 0:
            # Remove everything except preconversation text
            await self.update_display(preconversation_text)
            return

        # Find the cutoff point - everything after the last exchange we want to keep
        cutoff_line = user_line_indices[exchanges_to_keep - 1]

        # Find the start of the next exchange to remove
        if exchanges_to_keep < len(user_line_indices):
            next_exchange_start = user_line_indices[exchanges_to_keep]
        else:
            next_exchange_start = len(lines)

        # Build the text to keep and text to remove
        preserved_lines = lines[:next_exchange_start]
        preserved_text = "\n".join(preserved_lines)

        # Remove each exchange one by one with animation
        for exchange_idx in range(exchanges_to_remove):
            current_exchange_idx = len(user_line_indices) - 1 - exchange_idx

            if current_exchange_idx < 0:
                break

            # Find the range of lines for this exchange
            exchange_start = user_line_indices[current_exchange_idx]

            # Find the end of this exchange (start of next exchange or end of text)
            if current_exchange_idx + 1 < len(user_line_indices):
                exchange_end = user_line_indices[current_exchange_idx + 1]
            else:
                exchange_end = len(lines)

            # Build the text without this exchange
            remaining_lines = lines[:exchange_start]
            remaining_text = "\n".join(remaining_lines)

            # Animate the removal of this exchange
            exchange_lines = lines[exchange_start:exchange_end]
            exchange_text = "\n".join(exchange_lines)

            # Use the regular reverse stream for this exchange
            await self.reverse_stream(
                exchange_text,
                preserved_msg=remaining_text,
                delay=delay,
                preconversation_text=preconversation_text,
                acceleration_factor=acceleration_factor,
            )

            # Update the lines array for the next iteration
            lines = remaining_lines

            # Recalculate user line indices for remaining text
            user_line_indices = []
            for i, line in enumerate(lines):
                if line.strip().startswith(">"):
                    user_line_indices.append(i)

    async def fake_reverse_stream_text(
        self, user_message: str, delay: float = 0.08, acceleration_factor: float = 1.15
    ) -> None:
        """
        Continue reverse streaming by removing user message text word by word.

        Args:
            user_message: User message like "> How about a joke"
            delay: Base delay between word removals
            acceleration_factor: How much to accelerate the animation
        """
        # Extract prompt prefix and text content
        if user_message.startswith("> "):
            prompt_prefix = "> "
            text_content = user_message[2:].strip()
        else:
            prompt_prefix = ""
            text_content = user_message.strip()

        if not text_content:
            return

        # Tokenize the text content (not including prompt prefix)
        tokens = self.tokenize_text(text_content)
        groups = self.group_tokens_by_word(tokens)

        # Remove words from the end, similar to existing reverse stream logic
        chunks_to_remove = 1.0
        while any(group_type == "word" for group_type, _ in groups):
            chunks_this_round = round(chunks_to_remove)
            for _ in range(min(chunks_this_round, len(groups))):
                # Remove trailing spaces first
                while groups and groups[-1][0] == "space":
                    groups.pop()
                # Then remove the word
                if groups:
                    groups.pop()

            chunks_to_remove *= acceleration_factor

            # Reassemble remaining tokens
            remaining_tokens = []
            for _, grp in groups:
                remaining_tokens.extend(grp)
            remaining_text = self.reassemble_tokens(remaining_tokens)

            # Display prompt prefix + remaining text
            display_text = prompt_prefix + remaining_text
            await self.update_display("", display_text, force_full_clear=True)
            await asyncio.sleep(delay)

        # Final state: just the prompt prefix
        await self.update_display("", prompt_prefix, force_full_clear=True)

    async def fake_forward_stream_text(
        self, previous_message: str, delay: float = 0.06, current_prompt: str = "> "
    ) -> None:
        """
        Stream previous message word by word into the prompt area.

        Args:
            previous_message: The previous user message to stream in
            delay: Base delay between word additions
            current_prompt: Current prompt prefix (should be "> ")
        """
        # Clean the previous message - remove any existing prompt prefix
        if previous_message.startswith("> "):
            clean_message = previous_message[2:].strip()
        else:
            clean_message = previous_message.strip()

        if not clean_message:
            return

        # Tokenize the message into words
        tokens = self.tokenize_text(clean_message)
        groups = self.group_tokens_by_word(tokens)

        # Build up the message word by word
        accumulated_tokens = []

        for group_type, group_tokens in groups:
            accumulated_tokens.extend(group_tokens)

            # Reassemble current text
            current_text = self.reassemble_tokens(accumulated_tokens)
            display_text = current_prompt + current_text

            await self.update_display(
                "", display_text, no_spacing=True, force_full_clear=True
            )

            # Only add delay for word groups, not spaces
            if group_type == "word":
                await asyncio.sleep(delay)

    async def fake_forward_stream_styled_content(
        self,
        styled_content: str,
        delay: float = 0.02,
        acceleration_factor: float = 1.15,
    ) -> None:
        """
        Stream styled content back progressively with accelerating timing.

        Args:
            styled_content: Full styled content with ANSI sequences preserved
            delay: Base delay between chunk additions
            acceleration_factor: How much to accelerate the animation
        """
        if not styled_content.strip():
            return

        # Tokenize the styled content while preserving ANSI sequences
        tokens = self.tokenize_text(styled_content)
        groups = self.group_tokens_by_word(tokens)

        # Filter to only word groups for acceleration logic
        word_groups = [grp for group_type, grp in groups if group_type == "word"]

        # Build up the content progressively with acceleration
        accumulated_tokens = []
        chunks_to_add = 1.0
        group_index = 0

        while group_index < len(groups):
            chunks_this_round = round(chunks_to_add)

            # Add chunks for this round
            for _ in range(min(chunks_this_round, len(groups) - group_index)):
                group_type, group_tokens = groups[group_index]
                accumulated_tokens.extend(group_tokens)
                group_index += 1

                if group_index >= len(groups):
                    break

            # Reassemble current accumulated content
            current_content = self.reassemble_tokens(accumulated_tokens)

            # Use smart clearing for intermediate frames, force clear for final frame
            is_final_frame = group_index >= len(groups)
            await self.update_display(
                current_content, "", force_full_clear=is_final_frame
            )

            # Add delay and accelerate for next round
            await asyncio.sleep(delay)
            chunks_to_add *= acceleration_factor

    async def _yield(self) -> None:
        """Yield briefly to the event loop."""
        await asyncio.sleep(0)
