# animations.py

import asyncio, json, time

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
                if i: await asyncio.sleep(ts - self._stored_messages[i-1][1])
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

    async def reverse_stream(self, styled_text, preserved_msg="", delay=0.08, preconversation_text=""):
        if preconversation_text and styled_text.startswith(preconversation_text):
            conversation_text = styled_text[len(preconversation_text):].lstrip()
        else:
            conversation_text = styled_text

        lines = self._prepare_lines(conversation_text)
        no_spacing = not preserved_msg
        await self._reverse_stream_lines(lines, preserved_msg, no_spacing, delay, preconversation_text)
        await self._handle_punctuation(preserved_msg, delay)
        
        final_text = preconversation_text.rstrip()+"\n\n" if preconversation_text else ""
        await self.terminal.update_animated_display(final_text)

    def _prepare_lines(self, styled_text):
        lines = styled_text.splitlines()
        return [
            self.styles.split_into_styled_words(line) if line.strip() else []
            for line in lines
        ]

    async def _reverse_stream_lines(self, lines, preserved_msg, no_spacing, delay, preconversation_text=""):
        for line_idx in range(len(lines)-1, -1, -1):
            while lines[line_idx]:
                lines[line_idx].pop()
                formatted_lines = self.styles.format_styled_lines(lines, self._base_color)
                full_display = (preconversation_text.rstrip()+"\n\n") if preconversation_text else ""
                if formatted_lines:
                    full_display += formatted_lines
                await self.terminal.update_animated_display(
                    full_display, preserved_msg, no_spacing
                )
                await asyncio.sleep(delay)

    async def _handle_punctuation(self, preserved_msg, delay):
        if not preserved_msg:
            return

        base = preserved_msg.rstrip('?.!')
        if preserved_msg.endswith(('!', '?')):
            char = preserved_msg[-1]
            count = len(preserved_msg) - len(base)
            for i in range(count, 0, -1):
                await self.terminal.update_animated_display("", f"{base}{char*i}")
                await asyncio.sleep(delay)
        elif preserved_msg.endswith('.'):
            for i in range(3, 0, -1):
                await self.terminal.update_animated_display("", f"{base}{'.'*i}")
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