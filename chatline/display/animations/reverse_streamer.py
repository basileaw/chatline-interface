# display/animations/reverse_streamer.py

import asyncio
import re
import math
from typing import List, Dict, Tuple, Union

class ReverseStreamer:
    """
    Performs reverse streaming animation word-by-word, preserving ANSI sequences.
    
    This animation removes text word by word from the end, with configurable
    acceleration and preserved messages.
    """
    def __init__(self, style, terminal, base_color='GREEN'):
        """
        Initialize the reverse streamer.
        
        Args:
            style: StyleEngine instance for text styling
            terminal: DisplayTerminal instance for output
            base_color: Base color for the animation
        """
        self.style = style
        self.terminal = terminal
        self._base_color = self.style.get_base_color(base_color)

    @staticmethod
    def tokenize_text(text: str) -> List[Dict[str, str]]:
        """
        Tokenize text into ANSI and character tokens.
        
        Args:
            text: Input text to tokenize
            
        Returns:
            List of tokens, each with 'type' ('ansi' or 'char') and 'value'
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
                for char in part:
                    tokens.append({'type': 'char', 'value': char})
        return tokens

    @staticmethod
    def reassemble_tokens(tokens: List[Dict[str, str]]) -> str:
        """Convert tokens back into text."""
        return ''.join(token['value'] for token in tokens)

    @staticmethod
    def group_tokens_by_word(tokens: List[Dict[str, str]]) -> List[Tuple[str, List[Dict[str, str]]]]:
        """
        Group tokens into word and space groups, preserving ANSI sequences.
        
        Args:
            tokens: List of tokens to group
            
        Returns:
            List of tuples (group_type, tokens) where group_type is 'word' or 'space'
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

    async def update_display(
        self,
        content: str,
        preserved_msg: str = "",
        no_spacing: bool = False
    ) -> None:
        """
        Update the display with animated content.
        
        Args:
            content: Main content to display
            preserved_msg: Message to preserve during animation
            no_spacing: Whether to remove extra spacing
        """
        self.terminal.clear_screen()
        if content:
            if preserved_msg:
                self.terminal.write(preserved_msg + ("" if no_spacing else "\n\n"))
            self.terminal.write(content)
        else:
            self.terminal.write(preserved_msg)
            
        self.terminal.write("", newline=False)
        self.terminal.write(self.style.get_format('RESET'))
        await self._yield()

    async def reverse_stream(
        self,
        styled_text: str,
        preserved_msg: str = "",
        delay: float = 0.08,
        preconversation_text: str = "",
        acceleration_factor: float = 1.15
    ) -> None:
        """
        Perform reverse-stream animation word-by-word with acceleration.
        
        Args:
            styled_text: Text to animate
            preserved_msg: Message to preserve during animation
            delay: Delay between animation updates
            preconversation_text: Text displayed before the animated content
            acceleration_factor: Factor to increase chunks removed each round
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
            await self.update_display(full_display, preserved_msg, no_spacing)
            await asyncio.sleep(delay)

        await self._handle_punctuation(preserved_msg, delay)

        if preserved_msg:
            final_text = preconversation_text.rstrip() if preconversation_text else ""
        else:
            final_text = (preconversation_text.rstrip() if preconversation_text else "") + "\n\n"
        await self.update_display(final_text)

    async def _handle_punctuation(self, preserved_msg: str, delay: float) -> None:
        """
        Animate punctuation in the preserved message.
        
        Args:
            preserved_msg: Message containing punctuation to animate
            delay: Delay between animation frames
        """
        if not preserved_msg:
            return

        base = preserved_msg.rstrip('?.!')
        if preserved_msg.endswith(('!', '?')):
            char = preserved_msg[-1]
            count = len(preserved_msg) - len(base)
            for i in range(count, 0, -1):
                await self.update_display("", f"{base}{char * i}")
                await asyncio.sleep(delay)
        elif preserved_msg.endswith('.'):
            for i in range(3, 0, -1):
                await self.update_display("", f"{base}{'.' * i}")
                await asyncio.sleep(delay)

    async def _yield(self) -> None:
        """Yield briefly to the event loop."""
        await asyncio.sleep(0)