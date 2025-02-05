# conversation.py

import logging
import copy
import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime

@dataclass
class Message:
    role: str
    content: str
    turn_number: int = 0

@dataclass
class PrefaceContent:
    text: str
    color: str = None
    display_type: str = "text"

@dataclass
class ConversationState:
    messages: List[Dict[str, str]] = field(default_factory=list)
    turn_number: int = 0
    system_prompt: Optional[str] = None
    last_user_input: Optional[str] = None
    is_silent: bool = False
    prompt_display: str = ""
    preconversation_styled: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        return {k: v for k, v in self.__dict__.items()}
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ConversationState':
        return cls(**data)

    def create_snapshot(self) -> Dict:
        return copy.deepcopy(self.to_dict())

class StateManager:
    def __init__(self, logger=None):
        self.current_state = ConversationState()
        self.state_history: Dict[int, Dict] = {}
        self.logger = logger or logging.getLogger(__name__)
        
    def update_state(self, **kwargs) -> None:
        for key, value in kwargs.items():
            if hasattr(self.current_state, key):
                setattr(self.current_state, key, value)
        self.state_history[self.current_state.turn_number] = self.current_state.create_snapshot()
            
    def restore_state(self, turn_number: int) -> Optional[ConversationState]:
        if turn_number in self.state_history:
            self.current_state = ConversationState.from_dict(self.state_history[turn_number])
            return self.current_state
        return None
    
    def get_current_state(self) -> ConversationState:
        return self.current_state
    
    def clear_history(self) -> None:
        self.state_history.clear()
        self.current_state = ConversationState()

class Conversation:
    default_messages = {
        "system": (
            'Write in present tense. Write in third person. Use the following text styles:\n'
            '- "quotes" for dialogue\n'
            '- [Brackets...] for actions\n'
            '- underscores for emphasis\n'
            '- asterisks for bold text'),
        "user": (
            """Write the line: "[The machine powers on and hums...]\n\n"""
            """Then, start a new, 25-word paragraph."""
            """Begin with a greeting from the machine itself: " "Hey there," " """)
    }

    def __init__(self, terminal, generator_func, styles, animations_manager, system_prompt=None):
        self.terminal = terminal
        self.generator = generator_func
        self.styles = styles
        self.animations = animations_manager
        self.system_prompt = system_prompt
        self.messages = []
        self.state_manager = StateManager(logger=logging.getLogger(__name__))
        self.is_silent = False
        self.prompt = ""
        self.preconversation_text = []
        self.preconversation_styled = ""
        self._display_strategies = {
            "text": self.styles.create_display_strategy("text"),
            "panel": self.styles.create_display_strategy("panel")
        }
        self.state_manager.update_state(
            system_prompt=system_prompt,
            is_silent=False,
            prompt_display="",
            preconversation_styled=""
        )

    def start(self, messages=None):
        import asyncio
        try:
            asyncio.run(self._run_conversation(
                messages["system"] if messages else self.default_messages["system"],
                messages["user"] if messages else self.default_messages["user"],
                self.preconversation_text
            ))
        except KeyboardInterrupt:
            print("\nExiting...")
        finally:
            self.terminal._show_cursor()
            self.terminal._clear_screen()  
            self.terminal._write("\n")    

    async def _run_conversation(self, system_msg=None, intro_msg=None, preface_text=None):
        try:
            self.system_prompt = system_msg or self.default_messages["system"]
            self.state_manager.update_state(system_prompt=self.system_prompt)
            _, intro_styled, _ = await self.handle_intro(intro_msg or self.default_messages["user"], preface_text)
            
            while True:
                user_input = await self.terminal.get_user_input()
                if not user_input:
                    continue
                try:
                    cmd = user_input.lower().strip()
                    if cmd in ["edit", "retry"]:
                        _, intro_styled, _ = await self.handle_edit_or_retry(intro_styled, is_retry=cmd=="retry")
                    else:
                        _, intro_styled, _ = await self.handle_message(user_input, intro_styled)
                except Exception as e:
                    logging.error(f"Conversation error: {str(e)}", exc_info=True)
                    print(f"\nAn error occurred: {str(e)}")
        except Exception as e:
            logging.error(f"Critical error: {str(e)}", exc_info=True)
            raise
        finally:
            await self.terminal.update_display()

    async def _process_message(self, msg: str, silent: bool = False) -> Tuple[str, str]:
        try:
            current_state = self.state_manager.get_current_state()
            turn_number = current_state.turn_number + 1
            
            self.messages.append(Message("user", msg, turn_number))
            self.state_manager.update_state(
                turn_number=turn_number,
                last_user_input=msg,
                messages=await self.get_messages()
            )
            
            self.styles.set_output_color('GREEN')
            loader = self.animations.create_dot_loader(
                prompt="" if silent else f"> {msg}",
                no_animation=silent
            )
            
            messages = await self.get_messages()
            raw, styled = await loader.run_with_loading(self.generator(messages))
            
            if raw:
                self.messages.append(Message("assistant", raw, turn_number))
                self.state_manager.update_state(messages=await self.get_messages())
                
            return raw, styled
        except Exception as e:
            logging.error(f"Message processing error: {str(e)}", exc_info=True)
            return "", ""

    async def get_messages(self) -> List[Dict[str, str]]:
        base_messages = [{"role": m.role, "content": m.content} for m in self.messages]
        return ([{"role": "system", "content": self.system_prompt}] + base_messages) if self.system_prompt else base_messages

    async def _process_preface(self, text_list) -> str:
        if not text_list:
            return ""
        return ''.join([await self._format_preface_content(content) for content in text_list])

    async def _format_preface_content(self, content: PrefaceContent) -> str:
        self.styles.set_output_color(content.color)
        strategy = self._display_strategies[content.display_type]
        _, styled = await self.styles.write_styled(strategy.format(content))
        return styled

    async def handle_intro(self, intro_msg: str, preface_text: Optional[List] = None) -> Tuple[str, str, str]:
        self.preconversation_styled = await self._process_preface(preface_text)
        styled_panel = self.styles.append_single_blank_line(self.preconversation_styled)
        
        if styled_panel.strip():
            await self.terminal.update_display(styled_panel, preserve_cursor=True)
            
        raw, styled = await self._process_message(intro_msg, silent=True)
        full_styled = styled_panel + styled
        await self.terminal.update_display(full_styled)
        
        self.is_silent = True
        self.prompt = ""
        self.state_manager.update_state(
            is_silent=True,
            prompt_display="",
            preconversation_styled=self.preconversation_styled
        )
        
        return raw, full_styled, ""

    async def handle_message(self, user_input: str, intro_styled: str) -> Tuple[str, str, str]:
        await self.terminal.handle_scroll(intro_styled, f"> {user_input}", 0.08)
        raw, styled = await self._process_message(user_input)
        
        self.is_silent = False
        end_char = user_input[-1] if user_input.endswith(('?', '!')) else '.'
        self.prompt = f"> {user_input.rstrip('?.!')}{end_char * 3}"
        self.preconversation_styled = ""
        
        self.state_manager.update_state(
            is_silent=False,
            prompt_display=self.prompt,
            preconversation_styled=""
        )
        
        return raw, styled, self.prompt

    async def handle_edit_or_retry(self, intro_styled: str, is_retry: bool = False) -> Tuple[str, str, str]:
        current_turn = self.state_manager.get_current_state().turn_number
        
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
            self.messages = self.messages[:-2]
            self.state_manager.restore_state(current_turn - 1)
        
        if self.is_silent:
            raw, styled = await self._process_message(last_msg, silent=True)
            self.state_manager.update_state(
                is_silent=True,
                preconversation_styled=self.preconversation_styled
            )
            return raw, f"{self.preconversation_styled}\n{styled}", ""
        
        if is_retry:
            await self.terminal.clear()
            raw, styled = await self._process_message(last_msg)
        else:
            new_input = await self.terminal.get_user_input(default_text=last_msg, add_newline=False)
            if not new_input:
                return "", intro_styled, ""
            await self.terminal.clear()
            raw, styled = await self._process_message(new_input)
            last_msg = new_input
            
        end_char = last_msg[-1] if last_msg.endswith(('?', '!')) else '.'
        self.prompt = f"> {last_msg.rstrip('?.!')}{end_char * 3}"
        self.state_manager.update_state(prompt_display=self.prompt)
        return raw, styled, self.prompt

    def preface(self, text: str, color: Optional[str] = None, display_type: str = "panel") -> None:
        self.preconversation_text.append(PrefaceContent(text, color, display_type))
        self.state_manager.update_state(preconversation_styled=self.preconversation_styled)