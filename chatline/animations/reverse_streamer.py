# animations/reverse_streamer.py

import asyncio
import re

class ReverseStreamer:
    """
    Handles reverse streaming animation effects.
    
    Provides word-by-word reverse streaming while preserving ANSI escape sequences.
    """
    def __init__(self, styles, utilities=None, base_color='GREEN'):
        self.styles = styles
        self.utilities = utilities
        self._base_color = self.styles.get_base_color(base_color)

    @staticmethod
    def tokenize_text(text):
        """
        Tokenize the input text into a list of tokens.
        Each token is a dict with keys:
          - 'type': either 'ansi' or 'char'
          - 'value': the token text
        """
        ANSI_REGEX = re.compile(r'(\x1B\[[0-?]*[ -/]*[@-~])')
        tokens = []
        parts = re.split(ANSI_REGEX, text)
        for part in parts:
            if not part:
                continue
            if ANSI_REGEX.fullmatch(part):
                tokens.append({'type': 'ansi', 'value': part})
            else:
                # Break visible text into individual characters.
                for char in part:
                    tokens.append({'type': 'char', 'value': char})
        return tokens

    @staticmethod
    def reassemble_tokens(tokens):
        """Reassemble tokens back into a single string."""
        return ''.join(token['value'] for token in tokens)

    @staticmethod
    def group_tokens_by_word(tokens):
        """
        Group the token list into word groups. Each group is a tuple:
          (group_type, tokens)
        where group_type is 'word' (for non-space characters) or 'space' (for whitespace).
        ANSI tokens are merged into the current group.
        """
        groups = []
        current_group = []
        current_type = None  # 'word' or 'space'
        for token in tokens:
            if token['type'] == 'ansi':
                # ANSI tokens are added to the current group if it exists; otherwise, start a new 'word' group.
                if current_group:
                    current_group.append(token)
                else:
                    current_group = [token]
                    current_type = 'word'
            else:  # token is a visible character
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

    async def reverse_stream(self, styled_text, preserved_msg="", delay=0.08, preconversation_text=""):
        """
        Reverse-stream animation performed word-by-word.
        ANSI escape sequences are preserved intact by first tokenizing the text and then grouping
        visible characters into word groups.
        """
        if preconversation_text and styled_text.startswith(preconversation_text):
            conversation_text = styled_text[len(preconversation_text):].lstrip()
        else:
            conversation_text = styled_text

        # Tokenize the conversation text.
        tokens = self.tokenize_text(conversation_text)
        # Group the tokens into words and whitespace groups.
        groups = self.group_tokens_by_word(tokens)

        no_spacing = not preserved_msg

        # Remove one word group (and any trailing space group) at a time.
        while any(group_type == 'word' for group_type, _ in groups):
            # First, if the last group is a whitespace group, remove it.
            while groups and groups[-1][0] == 'space':
                groups.pop()
            if groups:
                # Remove the last word group.
                groups.pop()
            # Reassemble the remaining tokens.
            remaining_tokens = []
            for _, grp in groups:
                remaining_tokens.extend(grp)
            new_text = self.reassemble_tokens(remaining_tokens)
            if preconversation_text:
                full_display = preconversation_text.rstrip() + "\n\n" + new_text
            else:
                full_display = new_text
            await self.utilities.update_animated_display(full_display, preserved_msg, no_spacing)
            await asyncio.sleep(delay)

        await self._handle_punctuation(preserved_msg, delay)

        # Modified final text handling to prevent duplicate newlines
        if preserved_msg:
            # Don't add extra newlines if we have a preserved message
            final_text = (preconversation_text.rstrip() if preconversation_text else "")
        else:
            # Keep the double newline only when there's no preserved message
            final_text = (preconversation_text.rstrip() if preconversation_text else "") + "\n\n"
            
        await self.utilities.update_animated_display(final_text)

    async def _handle_punctuation(self, preserved_msg, delay):
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