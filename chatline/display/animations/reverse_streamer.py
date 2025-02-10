# animations/reverse_streamer.py

import asyncio
import re
import math

class ReverseStreamer:
    """Performs reverse streaming animation word-by-word, preserving ANSI sequences."""
    def __init__(self, styles, utilities=None, base_color='GREEN'):
        self.styles = styles
        self.utilities = utilities
        self._base_color = self.styles.get_base_color(base_color)

    @staticmethod
    def tokenize_text(text):
        """Tokenize text into tokens of type 'ansi' or 'char'."""
        ANSI_REGEX = re.compile(r'(\x1B\[[0-?]*[ -/]*[@-~])')
        tokens = []
        parts = re.split(ANSI_REGEX, text)
        for part in parts:
            if not part:
                continue
            if ANSI_REGEX.fullmatch(part):
                tokens.append({'type': 'ansi', 'value': part})
            else:
                for char in part:
                    tokens.append({'type': 'char', 'value': char})
        return tokens

    @staticmethod
    def reassemble_tokens(tokens):
        """Reassemble tokens back into a string."""
        return ''.join(token['value'] for token in tokens)

    @staticmethod
    def group_tokens_by_word(tokens):
        """
        Group tokens into tuples of (group_type, tokens), where group_type is 'word' or 'space'.
        ANSI tokens are merged into the current group.
        """
        groups = []
        current_group = []
        current_type = None  # 'word' or 'space'
        for token in tokens:
            if token['type'] == 'ansi':
                if current_group:
                    current_group.append(token)
                else:
                    current_group = [token]
                    current_type = 'word'
            else:
                if token['value'].isspace():
                    if current_group and current_type == 'space':
                        current_group.append(token)
                    elif current_group and current_type == 'word':
                        groups.append((current_type, current_group))
                        current_group = [token]
                        current_type = 'space'
                    else:
                        current_group = [token]
                        current_type = 'space'
                else:
                    if current_group and current_type == 'word':
                        current_group.append(token)
                    elif current_group and current_type == 'space':
                        groups.append((current_type, current_group))
                        current_group = [token]
                        current_type = 'word'
                    else:
                        current_group = [token]
                        current_type = 'word'
        if current_group:
            groups.append((current_type, current_group))
        return groups

    async def reverse_stream(
        self,
        styled_text,
        preserved_msg="",
        delay=0.08,
        preconversation_text="",
        acceleration_factor=1.15
    ):
        """
        Perform reverse-stream animation word-by-word with acceleration.
        
        Args:
            styled_text (str): Text to animate.
            preserved_msg (str): Message to preserve during animation.
            delay (float): Delay between animation updates.
            preconversation_text (str): Text displayed before the animated content.
            acceleration_factor (float): Factor to increase chunks removed each round.
        """
        if preconversation_text and styled_text.startswith(preconversation_text):
            conversation_text = styled_text[len(preconversation_text):].lstrip()
        else:
            conversation_text = styled_text

        tokens = self.tokenize_text(conversation_text)
        groups = self.group_tokens_by_word(tokens)
        no_spacing = not preserved_msg
        chunks_to_remove = 1.0

        while any(group_type == 'word' for group_type, _ in groups):
            chunks_this_round = round(chunks_to_remove)
            for _ in range(min(chunks_this_round, len(groups))):
                while groups and groups[-1][0] == 'space':
                    groups.pop()
                if groups:
                    groups.pop()
            chunks_to_remove *= acceleration_factor

            remaining_tokens = []
            for _, grp in groups:
                remaining_tokens.extend(grp)
            new_text = self.reassemble_tokens(remaining_tokens)
            full_display = (preconversation_text.rstrip() + "\n\n" + new_text
                            if preconversation_text else new_text)
            await self.utilities.update_animated_display(full_display, preserved_msg, no_spacing)
            await asyncio.sleep(delay)

        await self._handle_punctuation(preserved_msg, delay)

        if preserved_msg:
            final_text = preconversation_text.rstrip() if preconversation_text else ""
        else:
            final_text = (preconversation_text.rstrip() if preconversation_text else "") + "\n\n"
        await self.utilities.update_animated_display(final_text)

    async def _handle_punctuation(self, preserved_msg, delay):
        """Animate punctuation in the preserved message."""
        if not preserved_msg:
            return

        base = preserved_msg.rstrip('?.!')
        if preserved_msg.endswith(('!', '?')):
            char = preserved_msg[-1]
            count = len(preserved_msg) - len(base)
            for i in range(count, 0, -1):
                await self.utilities.update_animated_display("", f"{base}{char * i}")
                await asyncio.sleep(delay)
        elif preserved_msg.endswith('.'):
            for i in range(3, 0, -1):
                await self.utilities.update_animated_display("", f"{base}{'.' * i}")
                await asyncio.sleep(delay)
