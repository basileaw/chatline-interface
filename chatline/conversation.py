import logging
from typing import List, Dict, Any, Tuple, Optional, Protocol
from dataclasses import dataclass
from rich.console import Console
from rich.panel import Panel
from functools import partial

@dataclass
class Message:
    role: str
    content: str

@dataclass
class PrefaceContent:
    text: str
    color: Optional[str]
    display_type: str = "text"

class DisplayStrategy(Protocol):
    def format(self, content: PrefaceContent) -> str: ...
    def get_visible_length(self, text: str) -> int: ...

class TextDisplayStrategy:
    def __init__(self, styles): self.styles = styles
    def format(self, content: PrefaceContent) -> str: return content.text + "\n"
    def get_visible_length(self, text: str) -> int: return self.styles.get_visible_length(text)

class PanelDisplayStrategy:
    def __init__(self, styles):
        self.styles = styles
        self.console = Console(force_terminal=True, color_system="truecolor", record=True)
    def format(self, content: PrefaceContent) -> str:
        with self.console.capture() as c:
            self.console.print(Panel(content.text.rstrip(), style=content.color or ""))
        return c.get()
    def get_visible_length(self, text: str) -> int:
        return self.styles.get_visible_length(text) + 4

class Conversation:
    @staticmethod
    def get_default_messages() -> Tuple[str, str]:
        return (
            'Be helpful, concise, and honest. Use text styles:\n'
            '- "quotes" for dialogue\n'
            '- [brackets] for observations\n'
            '- underscores for emphasis\n'
            '- asterisks for bold text',
            "Introduce yourself in 3 lines, 7 words each..."
        )

    def __init__(self, terminal, generator_func: Any, styles, stream, animations_manager, system_prompt: str = None):
        self.terminal = terminal
        self.generator = generator_func
        self.styles = styles
        self.stream = stream
        self.animations = animations_manager
        self.system_prompt = system_prompt
        self.messages: List[Message] = []
        self.is_silent = False
        self.prompt = ""
        self.preconversation_text: List[PrefaceContent] = []
        self.preconversation_styled = ""
        self._display_strategies = {
            "text": TextDisplayStrategy(styles),
            "panel": PanelDisplayStrategy(styles)
        }

    def _append_single_blank_line(self, styled_text: str) -> str:
        if styled_text.strip():
            return styled_text.rstrip('\n') + "\n\n"
        return styled_text

    def preface(self, text: str, color: Optional[str] = None, display_type: str = "panel") -> None:
        self.preconversation_text.append(PrefaceContent(text, color, display_type))

    def start(self, system_msg: str = None, intro_msg: str = None) -> None:
        self.run_conversation(system_msg, intro_msg, self.preconversation_text)

    def _get_last_user_message(self) -> Optional[str]:
        return next((m.content for m in reversed(self.messages) if m.role == "user"), None)

    async def get_messages(self) -> List[Dict[str, str]]:
        base = [{"role": "system", "content": self.system_prompt}] if self.system_prompt else []
        return base + [{"role": m.role, "content": m.content} for m in self.messages]

    async def _process_message(self, msg: str, silent=False) -> Tuple[str, str]:
        self.messages.append(Message("user", msg))
        self.stream.set_base_color('GREEN')
        loader = self.animations.create_dot_loader(
            prompt="" if silent else f"> {msg}",
            output_handler=self.stream,
            no_animation=silent
        )
        raw, styled = await loader.run_with_loading(self.generator(await self.get_messages()))
        self.messages.append(Message("assistant", raw))
        return raw, styled

    async def _process_preconversation_text(self, text_list: List[PrefaceContent]) -> str:
        if not text_list: return ""
        out = ""
        for content in text_list:
            self.stream.set_base_color(content.color)
            strat = self._display_strategies[content.display_type]
            formatted = strat.format(content)
            _, styled = await self.stream.add(formatted)
            out += styled
        return out

    async def handle_intro(self, intro_msg: str, preconversation_text: List[PrefaceContent] = None) -> Tuple[str, str, str]:
        self.preconversation_styled = await self._process_preconversation_text(preconversation_text)
        panel_with_blank = self._append_single_blank_line(self.preconversation_styled)
        if panel_with_blank.strip():
            await self.terminal.update_display(panel_with_blank, preserve_cursor=True)
        raw, styled = await self._process_message(intro_msg, silent=True)
        full_styled = panel_with_blank + styled
        await self.terminal.update_display(full_styled)
        self.is_silent = True
        self.prompt = ""
        return raw, full_styled, ""

    async def handle_message(self, user_input: str, intro_styled: str) -> Tuple[str, str, str]:
        await self.terminal.handle_scroll(intro_styled, f"> {user_input}", 0.08)
        raw, styled = await self._process_message(user_input)
        self.is_silent = False
        end_char = '.' if not user_input.endswith(('?', '!')) else user_input[-1]
        self.prompt = f"> {user_input.rstrip('?.!')}{end_char * 3}"
        self.preconversation_styled = ""
        return raw, styled, self.prompt

    async def handle_edit_or_retry(self, intro_styled: str, is_retry: bool = False) -> Tuple[str, str, str]:
        rev_streamer = self.animations.create_reverse_streamer()
        await rev_streamer.reverse_stream(intro_styled, "" if self.is_silent else self.prompt, preconversation_text=self.preconversation_styled)
        last_msg = self._get_last_user_message()
        if not last_msg: return "", intro_styled, ""
        if self.is_silent:
            raw, styled = await self._process_message(last_msg, silent=True)
            full_styled = f"{self.preconversation_styled}\n{styled}"
            return raw, full_styled, ""
        if is_retry:
            await self.terminal.clear()
            raw, styled = await self._process_message(last_msg, silent=False)
            end_char = '.' if not last_msg.endswith(('?', '!')) else last_msg[-1]
            self.prompt = f"> {last_msg.rstrip('?.!')}{end_char * 3}"
            return raw, styled, self.prompt
        else:
            new_input = await self.terminal.get_user_input(default_text=last_msg, add_newline=False)
            if not new_input: return "", intro_styled, ""
            await self.terminal.clear()
            raw, styled = await self._process_message(new_input, silent=False)
            end_char = '.' if not new_input.endswith(('?', '!')) else new_input[-1]
            self.prompt = f"> {new_input.rstrip('?.!')}{end_char * 3}"
            return raw, styled, self.prompt

    async def handle_edit(self, intro_styled: str) -> Tuple[str, str, str]:
        return await self.handle_edit_or_retry(intro_styled, is_retry=False)

    async def handle_retry(self, intro_styled: str) -> Tuple[str, str, str]:
        return await self.handle_edit_or_retry(intro_styled, is_retry=True)

    def run_conversation(self, system_msg: str = None, intro_msg: str = None,
                         preconversation_text: List[PrefaceContent] = None):
        import asyncio
        asyncio.run(self._run_conversation(system_msg, intro_msg, preconversation_text))

    async def _run_conversation(self, system_msg: str = None, intro_msg: str = None,
                                preconversation_text: List[PrefaceContent] = None):
        try:
            if system_msg is None or intro_msg is None:
                system_msg, intro_msg = self.get_default_messages()
            self.system_prompt = system_msg
            _, intro_styled, _ = await self.handle_intro(intro_msg, preconversation_text)
            while True:
                user = await self.terminal.get_user_input()
                if not user: continue
                try:
                    cmd = user.lower().strip()
                    if cmd == "edit":
                        _, intro_styled, _ = await self.handle_edit(intro_styled)
                    elif cmd == "retry":
                        _, intro_styled, _ = await self.handle_retry(intro_styled)
                    else:
                        _, intro_styled, _ = await self.handle_message(user, intro_styled)
                except Exception as e:
                    logging.error(f"Error processing message: {str(e)}", exc_info=True)
                    print(f"\nAn error occurred: {str(e)}")
        except KeyboardInterrupt:
            print("\nExiting...")
        except Exception as e:
            logging.error(f"Critical error: {str(e)}", exc_info=True)
            raise
        finally:
            await self.terminal.update_display()
