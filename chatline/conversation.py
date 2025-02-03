# conversation.py

import logging
from dataclasses import dataclass

@dataclass
class Message:
    role: str
    content: str

@dataclass
class PrefaceContent:
    text: str
    color: str = None
    display_type: str = "text"

class Conversation:
    def __init__(self, terminal, generator_func, styles, animations_manager, system_prompt=None):
        self.terminal = terminal
        self.generator = generator_func
        self.styles = styles
        self.animations = animations_manager
        self.system_prompt = system_prompt
        self.messages = []
        self.is_silent = False
        self.prompt = ""
        self.preconversation_text = []
        self.preconversation_styled = ""
        self._display_strategies = {
            "text": self.styles.create_display_strategy("text"),
            "panel": self.styles.create_display_strategy("panel")
        }

    default_messages = {
        "system": ('Be helpful, concise, and honest. Use text styles:\n'
                  '- "quotes" for dialogue\n'
                  '- [brackets] for observations\n'
                  '- underscores for emphasis\n'
                  '- asterisks for bold text'),
        "user": "Introduce yourself in 3 lines, 7 words each..."
    }
    
    def start(self, messages=None):
        import asyncio
        try:
            if messages is None:
                messages = self.default_messages
            asyncio.run(self._run_conversation(messages["system"], messages["user"], self.preconversation_text))
        except KeyboardInterrupt:
            print("\nExiting...")
        finally:
            self.terminal._show_cursor()

    async def _run_conversation(self, system_msg=None, intro_msg=None, preface_text=None):
        try:
            if system_msg is None or intro_msg is None:
                system_msg = self.default_messages["system"]
                intro_msg = self.default_messages["user"]
            
            self.system_prompt = system_msg
            _, intro_styled, _ = await self.handle_intro(intro_msg, preface_text)
            
            while True:
                user_input = await self.terminal.get_user_input()
                if not user_input:
                    continue
                    
                try:
                    cmd = user_input.lower().strip()
                    if cmd == "edit":
                        _, intro_styled, _ = await self.handle_edit(intro_styled)
                    elif cmd == "retry":
                        _, intro_styled, _ = await self.handle_retry(intro_styled)
                    else:
                        _, intro_styled, _ = await self.handle_message(user_input, intro_styled)
                except Exception as e:
                    logging.error("Conversation error: %s", str(e), exc_info=True)
                    print(f"\nAn error occurred: {str(e)}")
                    
        except Exception as e:
            logging.error("Critical error: %s", str(e), exc_info=True)
            raise
        finally:
            await self.terminal.update_display()
            
    async def _process_message(self, msg, silent=False):
        try:
            self.messages.append(Message("user", msg))
            self.styles.set_output_color('GREEN')
            
            loader = self.animations.create_dot_loader(
                prompt="" if silent else f"> {msg}",
                no_animation=silent
            )
            
            messages = await self.get_messages()
            raw, styled = await loader.run_with_loading(self.generator(messages))
            
            if raw:
                self.messages.append(Message("assistant", raw))
            return raw, styled
            
        except Exception as e:
            logging.error("Message processing error: %s", str(e), exc_info=True)
            return "", ""

    async def get_messages(self):
        if self.system_prompt:
            return [{"role": "system", "content": self.system_prompt}] + \
                   [{"role": m.role, "content": m.content} for m in self.messages]
        return [{"role": m.role, "content": m.content} for m in self.messages]

    async def _process_preface(self, text_list):
        if not text_list:
            return ""
        out = ""
        for content in text_list:
            self.styles.set_output_color(content.color)
            strategy = self._display_strategies[content.display_type]
            _, styled = await self.styles.write_styled(strategy.format(content))
            out += styled
        return out

    async def handle_intro(self, intro_msg, preface_text=None):
        self.preconversation_styled = await self._process_preface(preface_text)
        styled_panel = self.styles.append_single_blank_line(self.preconversation_styled)
        
        if styled_panel.strip():
            await self.terminal.update_display(styled_panel, preserve_cursor=True)
            
        raw, styled = await self._process_message(intro_msg, silent=True)
        full_styled = styled_panel + styled
        await self.terminal.update_display(full_styled)
        
        self.is_silent = True
        self.prompt = ""
        return raw, full_styled, ""

    async def handle_message(self, user_input, intro_styled):
        await self.terminal.handle_scroll(intro_styled, f"> {user_input}", 0.08)
        raw, styled = await self._process_message(user_input)
        
        self.is_silent = False
        end_char = '.' if not user_input.endswith(('?', '!')) else user_input[-1]
        self.prompt = f"> {user_input.rstrip('?.!')}{end_char * 3}"
        self.preconversation_styled = ""
        
        return raw, styled, self.prompt

    async def handle_edit_or_retry(self, intro_styled, is_retry=False):
        rev_streamer = self.animations.create_reverse_streamer()
        await rev_streamer.reverse_stream(
            intro_styled, 
            "" if self.is_silent else self.prompt,
            preconversation_text=self.preconversation_styled
        )
        
        last_msg = next((m.content for m in reversed(self.messages) if m.role == "user"), None)
        if not last_msg:
            return "", intro_styled, ""
        
        if len(self.messages) >= 2 and self.messages[-2].role == "user":
            self.messages.pop()
            self.messages.pop()
        
        if self.is_silent:
            raw, styled = await self._process_message(last_msg, silent=True)
            return raw, f"{self.preconversation_styled}\n{styled}", ""
            
        if is_retry:
            await self.terminal.clear()
            raw, styled = await self._process_message(last_msg)
            end_char = '.' if not last_msg.endswith(('?', '!')) else last_msg[-1]
            self.prompt = f"> {last_msg.rstrip('?.!')}{end_char * 3}"
            return raw, styled, self.prompt
        else:
            new_input = await self.terminal.get_user_input(default_text=last_msg, add_newline=False)
            if not new_input:
                return "", intro_styled, ""
            await self.terminal.clear()
            raw, styled = await self._process_message(new_input)
            end_char = '.' if not new_input.endswith(('?', '!')) else new_input[-1]
            self.prompt = f"> {new_input.rstrip('?.!')}{end_char * 3}"
            return raw, styled, self.prompt

    async def handle_edit(self, intro_styled):
        return await self.handle_edit_or_retry(intro_styled, is_retry=False)

    async def handle_retry(self, intro_styled):
        return await self.handle_edit_or_retry(intro_styled, is_retry=True)

    def preface(self, text, color=None, display_type="panel"):
        self.preconversation_text.append(PrefaceContent(text, color, display_type))