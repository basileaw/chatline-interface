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
        # Use full screen clearing for punctuation animation
        if force_full_clear:
            self.terminal.clear_screen()
        else:
            # Move cursor to home position rather than clearing screen each time
            self.terminal.write("\033[H")

        # Build full output content first
        output = ""
        if preserved_msg:
            output += preserved_msg
            if not no_spacing:
                output += "\n"

        if content:
            output += content

        # Write the full content in one go
        self.terminal.write(output)

        if not force_full_clear:
            # Clear from cursor to end of screen (rather than full clear)
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

    async def _yield(self) -> None:
        """Yield briefly to the event loop."""
        await asyncio.sleep(0)
