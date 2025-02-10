# conversation.py

import logging
import copy
import asyncio
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from datetime import datetime

# -------------------------------
# Data Classes (unchanged)
# -------------------------------

@dataclass
class Message:
    """Represents a single message in the conversation."""
    role: str
    content: str
    turn_number: int = 0

@dataclass
class PrefaceContent:
    """Configuration for preface text display."""
    text: str
    color: Optional[str] = None
    display_type: str = "text"

@dataclass
class ConversationState:
    """
    Maintains the current state of the conversation.
    """
    messages: List[Dict[str, str]] = field(default_factory=list)
    turn_number: int = 0
    system_prompt: Optional[str] = None
    last_user_input: Optional[str] = None
    is_silent: bool = False
    prompt_display: str = ""
    preconversation_styled: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        """Convert state to dictionary for storage."""
        return {k: v for k, v in self.__dict__.items()}
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ConversationState':
        """Create state instance from dictionary."""
        return cls(**data)

# -------------------------------
# History Class
# -------------------------------

class ConversationHistory:
    """
    Manages conversation state and state history.
    """
    def __init__(self):
        self.current_state = ConversationState()
        self.state_history: Dict[int, Dict] = {}

    def create_state_snapshot(self) -> Dict:
        """Create a deep copy of the current state."""
        return copy.deepcopy(self.current_state.to_dict())

    def update_state(self, **kwargs) -> None:
        """
        Update the current state with new values and store a snapshot.
        """
        for key, value in kwargs.items():
            if hasattr(self.current_state, key):
                setattr(self.current_state, key, value)
        self.state_history[self.current_state.turn_number] = self.create_state_snapshot()

    def restore_state(self, turn_number: int) -> Optional[ConversationState]:
        """
        Restore state from a specific turn number.
        """
        if turn_number in self.state_history:
            self.current_state = ConversationState.from_dict(self.state_history[turn_number])
            return self.current_state
        return None

    def clear_state_history(self) -> None:
        """Clear the state history and reset the current state."""
        self.state_history.clear()
        self.current_state = ConversationState()

# -------------------------------
# Messages Class
# -------------------------------

class ConversationMessages:
    """
    Manages conversation messages.
    """
    def __init__(self):
        self.messages: List[Message] = []

    def add_message(self, role: str, content: str, turn_number: int) -> None:
        """Append a new message to the history."""
        self.messages.append(Message(role, content, turn_number))

    async def get_messages(self, system_prompt: Optional[str] = None) -> List[Dict[str, str]]:
        """
        Get the message history as a list of dictionaries.
        If a system prompt is provided, prepend it.
        """
        base_messages = [{"role": m.role, "content": m.content} for m in self.messages]
        if system_prompt:
            return [{"role": "system", "content": system_prompt}] + base_messages
        return base_messages

    def remove_last_n_messages(self, n: int) -> None:
        """Remove the last n messages."""
        if n <= len(self.messages):
            self.messages = self.messages[:-n]
        else:
            self.messages = []

# -------------------------------
# Actions Class
# -------------------------------

class ConversationActions:
    """
    Handles the actions and flow of the conversation.
    """
    def __init__(self, display, generator_func, history: ConversationHistory, messages: ConversationMessages):
        self.display = display
        self.terminal = display.terminal      # Terminal operations
        self.io = display.io                  # Display I/O
        self.styles = display.styles          # Text styling
        self.animations = display.animations  # Animated effects
        self.generator = generator_func

        self.history = history
        self.messages = messages
        self.logger = logging.getLogger(__name__)

        # Conversation-specific variables
        self.is_silent = False
        self.prompt = ""
        self.preconversation_text: List[PrefaceContent] = []
        self.preconversation_styled = ""
        self._display_strategies = {
            "text": self.styles.create_display_strategy("text"),
            "panel": self.styles.create_display_strategy("panel")
        }

    async def _process_message(self, msg: str, silent: bool = False) -> Tuple[str, str]:
        """
        Process a user message and generate a response.
        """
        try:
            turn_number = self.history.current_state.turn_number + 1

            # Add user message and update state
            self.messages.add_message("user", msg, turn_number)
            state_msgs = await self.messages.get_messages(self.history.current_state.system_prompt)
            self.history.update_state(
                turn_number=turn_number,
                last_user_input=msg,
                messages=state_msgs
            )

            self.styles.set_output_color('GREEN')
            loader = self.animations.create_dot_loader(
                prompt="" if silent else f"> {msg}",
                no_animation=silent
            )

            msgs = await self.messages.get_messages(self.history.current_state.system_prompt)
            raw, styled = await loader.run_with_loading(self.generator(msgs))

            if raw:
                self.messages.add_message("assistant", raw, turn_number)
                state_msgs = await self.messages.get_messages(self.history.current_state.system_prompt)
                self.history.update_state(messages=state_msgs)

            return raw, styled
        except Exception as e:
            self.logger.error(f"Message processing error: {str(e)}", exc_info=True)
            return "", ""

    async def _process_preface(self, text_list: List[PrefaceContent]) -> str:
        """Process list of preface content into styled text."""
        if not text_list:
            return ""
        styled_parts = []
        for content in text_list:
            formatted = await self._format_preface_content(content)
            styled_parts.append(formatted)
        return ''.join(styled_parts)

    async def _format_preface_content(self, content: PrefaceContent) -> str:
        """Format a single preface content item."""
        self.styles.set_output_color(content.color)
        strategy = self._display_strategies[content.display_type]
        _, styled = await self.styles.write_styled(strategy.format(content))
        return styled

    async def handle_intro(self, intro_msg: str) -> Tuple[str, str, str]:
        """
        Handle the initial message of the conversation.
        """
        self.preconversation_styled = await self._process_preface(self.preconversation_text)
        styled_panel = self.styles.append_single_blank_line(self.preconversation_styled)

        if styled_panel.strip():
            await self.io.update_display(styled_panel, preserve_cursor=True)

        raw, styled = await self._process_message(intro_msg, silent=True)
        full_styled = styled_panel + styled
        await self.io.update_display(full_styled)

        self.is_silent = True
        self.prompt = ""
        self.history.update_state(
            is_silent=True,
            prompt_display="",
            preconversation_styled=self.preconversation_styled
        )

        return raw, full_styled, ""

    async def handle_message(self, user_input: str, intro_styled: str) -> Tuple[str, str, str]:
        """
        Handle a regular user message.
        """
        await self.io.handle_scroll(intro_styled, f"> {user_input}", 0.08)
        raw, styled = await self._process_message(user_input)

        self.is_silent = False
        end_char = user_input[-1] if user_input.endswith(('?', '!')) else '.'
        self.prompt = f"> {user_input.rstrip('?.!')}{end_char * 3}"
        self.preconversation_styled = ""

        self.history.update_state(
            is_silent=False,
            prompt_display=self.prompt,
            preconversation_styled=""
        )

        return raw, styled, self.prompt

    async def handle_edit_or_retry(self, intro_styled: str, is_retry: bool = False) -> Tuple[str, str, str]:
        """
        Handle edit or retry commands.
        """
        current_turn = self.history.current_state.turn_number

        rev_streamer = self.animations.create_reverse_streamer()
        await rev_streamer.reverse_stream(
            intro_styled, 
            "" if self.is_silent else self.prompt,
            preconversation_text=self.preconversation_styled
        )

        # Locate the last user message
        last_msg = next((m.content for m in reversed(self.messages.messages) if m.role == "user"), None)
        if not last_msg:
            return "", intro_styled, ""

        if len(self.messages.messages) >= 2 and self.messages.messages[-2].role == "user":
            # Remove last two messages (user and assistant) and restore state
            self.messages.remove_last_n_messages(2)
            self.history.restore_state(current_turn - 1)

        if self.is_silent:
            raw, styled = await self._process_message(last_msg, silent=True)
            self.history.update_state(
                is_silent=True,
                preconversation_styled=self.preconversation_styled
            )
            return raw, f"{self.preconversation_styled}\n{styled}", ""

        if is_retry:
            await self.io.clear()
            raw, styled = await self._process_message(last_msg)
        else:
            new_input = await self.terminal.get_user_input(default_text=last_msg, add_newline=False)
            if not new_input:
                return "", intro_styled, ""
            await self.io.clear()
            raw, styled = await self._process_message(new_input)
            last_msg = new_input

        end_char = last_msg[-1] if last_msg.endswith(('?', '!')) else '.'
        self.prompt = f"> {last_msg.rstrip('?.!')}{end_char * 3}"
        self.history.update_state(prompt_display=self.prompt)
        return raw, styled, self.prompt

    async def run_conversation(self, system_msg: str, intro_msg: str):
        """
        Run the conversation loop with the initial messages.
        """
        try:
            self.history.current_state.system_prompt = system_msg
            _, intro_styled, _ = await self.handle_intro(intro_msg)

            while True:
                user_input = await self.terminal.get_user_input()
                if not user_input:
                    continue

                cmd = user_input.lower().strip()
                if cmd in ["edit", "retry"]:
                    _, intro_styled, _ = await self.handle_edit_or_retry(
                        intro_styled, 
                        is_retry=cmd == "retry"
                    )
                else:
                    _, intro_styled, _ = await self.handle_message(user_input, intro_styled)
        except Exception as e:
            self.logger.error(f"Critical error: {str(e)}", exc_info=True)
            raise
        finally:
            await self.io.update_display()

    def add_preface(self, text: str, color: Optional[str] = None, display_type: str = "panel") -> None:
        """
        Add preface content to the conversation.
        """
        self.preconversation_text.append(PrefaceContent(text, color, display_type))
        self.history.update_state(preconversation_styled=self.preconversation_styled)

# -------------------------------
# Coordinator / Wrapper Class
# -------------------------------

class Conversation:
    """
    Coordinator class exposing only 'start' and 'preface'.
    All other functionality is handled internally.
    """
    def __init__(self, display, generator_func):
        self.display = display
        self._history = ConversationHistory()
        self._messages = ConversationMessages()
        self._actions = ConversationActions(display, generator_func, self._history, self._messages)
        self._logger = logging.getLogger(__name__)

    def preface(self, text: str, color: Optional[str] = None, display_type: str = "panel") -> None:
        """
        Add preface content to the conversation.
        """
        self._actions.add_preface(text, color, display_type)

    def start(self, messages: Dict[str, str]) -> None:
        """
        Start the conversation with the provided messages.
        
        Expects a dictionary with 'system' and 'user' keys.
        """
        if not messages or 'system' not in messages or 'user' not in messages:
            raise ValueError("Both system and user messages are required")
        try:
            asyncio.run(self._actions.run_conversation(messages['system'], messages['user']))
        except KeyboardInterrupt:
            print("\nExiting...")
        finally:
            self.display.terminal.reset()
