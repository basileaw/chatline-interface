# animations.py

import asyncio, json, time, re

class AsyncDotLoader:
    def __init__(self, styles, prompt="", no_animation=False):
        self.styles = styles
        self.prompt = prompt.rstrip('.?!')
        self.no_anim = no_animation
        self.dot_char = '.' if prompt.endswith('.') or not prompt.endswith(('?','!')) else prompt[-1]
        self.dots = int(prompt.endswith(('.','?','!')))
        self.animation_complete = asyncio.Event()
        self.animation_task = None
        self.resolved = False
        self.terminal = None
        self._stored_messages = []

    async def _animate(self):
        try:
            while not self.animation_complete.is_set():
                await self.terminal.write_loading_state(self.prompt, self.dots, self.dot_char)
                await asyncio.sleep(0.4)
                if self.resolved and self.dots == 3:
                    await self.terminal.write_loading_state(self.prompt, 3, self.dot_char)
                    self.terminal._write('\n\n')
                    break
                self.dots = min(self.dots+1, 3) if self.resolved else (self.dots+1) % 4
            self.animation_complete.set()
        except Exception as e:
            self.animation_complete.set()
            raise e

    async def _handle_message_chunk(self, chunk, first_chunk):
        raw = styled = ""
        if not (c := chunk.strip()).startswith("data: ") or c == "data: [DONE]":
            return raw, styled

        try:
            if txt := json.loads(c[6:])["choices"][0]["delta"].get("content", ""):
                if first_chunk:
                    self.resolved = True
                    if not self.no_anim:
                        await self.animation_complete.wait()

                if not self.animation_complete.is_set():
                    self._stored_messages.append((txt, time.time()))
                else:
                    r, s = await self._process_stored_messages()
                    r2, s2 = await self.styles.write_styled(txt)
                    raw = r + r2
                    styled = s + s2
                await asyncio.sleep(0.01)
        except json.JSONDecodeError:
            pass

        return raw, styled

    async def _process_stored_messages(self):
        raw = styled = ""
        if self._stored_messages:
            self._stored_messages.sort(key=lambda x: x[1])
            for i, (text, ts) in enumerate(self._stored_messages):
                if i:
                    await asyncio.sleep(ts - self._stored_messages[i-1][1])
                r, s = await self.styles.write_styled(text)
                raw += r
                styled += s
            self._stored_messages.clear()
        return raw, styled

    async def run_with_loading(self, stream):
        if not self.styles:
            raise ValueError("styles must be provided")

        raw = styled = ""
        first_chunk = True

        if not self.no_anim:
            self.animation_task = asyncio.create_task(self._animate())
            await asyncio.sleep(0.01)

        try:
            if hasattr(stream, '__aiter__'):
                async for chunk in stream:
                    r, s = await self._handle_message_chunk(chunk, first_chunk)
                    raw += r
                    styled += s
                    first_chunk = False
            else:
                for chunk in stream:
                    r, s = await self._handle_message_chunk(chunk, first_chunk)
                    raw += r
                    styled += s
                    first_chunk = False

        finally:
            self.resolved = True
            self.animation_complete.set()
            if self.animation_task:
                await self.animation_task

            r, s = await self._process_stored_messages()
            raw += r
            styled += s

            r, s = await self.styles.flush_styled()
            raw += r
            styled += s

            return raw, styled

class ReverseStreamer:
    def __init__(self, styles, terminal=None, base_color='GREEN'):
        self.styles = styles
        self.terminal = terminal
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
            await self.terminal.update_animated_display(full_display, preserved_msg, no_spacing)
            await asyncio.sleep(delay)

        await self._handle_punctuation(preserved_msg, delay)

        # Modified final text handling to prevent duplicate newlines
        if preserved_msg:
            # Don't add extra newlines if we have a preserved message
            final_text = (preconversation_text.rstrip() if preconversation_text else "")
        else:
            # Keep the double newline only when there's no preserved message
            final_text = (preconversation_text.rstrip() if preconversation_text else "") + "\n\n"
            
        await self.terminal.update_animated_display(final_text)

    async def _handle_punctuation(self, preserved_msg, delay):
        if not preserved_msg:
            return

        base = preserved_msg.rstrip('?.!')
        if preserved_msg.endswith(('!', '?')):
            char = preserved_msg[-1]
            count = len(preserved_msg) - len(base)
            for i in range(count, 0, -1):
                await self.terminal.update_animated_display("", f"{base}{char * i}")
                await asyncio.sleep(delay)
        elif preserved_msg.endswith('.'):
            for i in range(3, 0, -1):
                await self.terminal.update_animated_display("", f"{base}{'.' * i}")
                await asyncio.sleep(delay)

class Animations:
    def __init__(self, terminal, styles):
        self.terminal = terminal
        self.styles = styles

    def create_dot_loader(self, prompt, no_animation=False):
        loader = AsyncDotLoader(self.styles, prompt, no_animation)
        loader.terminal = self.terminal
        return loader

    def create_reverse_streamer(self, base_color='GREEN'):
        return ReverseStreamer(self.styles, self.terminal, base_color)