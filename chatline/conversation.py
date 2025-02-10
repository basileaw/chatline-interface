# conversation.py

import logging
import copy
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime

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
    color: str = None
    display_type: str = "text"

@dataclass
class ConversationState:
    """
    Maintains the current state of the conversation.
    
    This class tracks all stateful elements including message history,
    display configuration, and timing information.
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

class Conversation:
    """
    Manages conversation flow and state.
    
    This class coordinates between the display system and message generation,
    handling user input, message processing, and display updates while
    maintaining conversation state.
    """
    def __init__(self, display, generator_func):
        """
        Initialize a conversation instance.
        
        Args:
            display: Display instance for managing terminal display operations
            generator_func: Async function that generates responses
        """
        self.display = display
        # Store direct references to display components
        self.terminal = display.terminal  # For terminal operations
        self.io = display.io              # For display I/O
        self.styles = display.styles      # For text styling
        self.animations = display.animations  # For animated effects
        
        self.generator = generator_func
        self.messages = []
        self.logger = logging.getLogger(__name__)
        
        # Initialize state management
        self.current_state = ConversationState()
        self.state_history = {}
        
        # Display configuration
        self.is_silent = False
        self.prompt = ""
        self.preconversation_text = []
        self.preconversation_styled = ""
        self._display_strategies = {
            "text": self.styles.create_display_strategy("text"),
            "panel": self.styles.create_display_strategy("panel")
        }

    def create_state_snapshot(self) -> Dict:
        """Create a deep copy of the current state."""
        return copy.deepcopy(self.current_state.to_dict())

    def update_state(self, **kwargs) -> None:
        """
        Update the current state with new values.
        
        Updates specified state attributes and saves a snapshot in history.
        """
        for key, value in kwargs.items():
            if hasattr(self.current_state, key):
                setattr(self.current_state, key, value)
        self.state_history[self.current_state.turn_number] = self.create_state_snapshot()

    def restore_state(self, turn_number: int) -> Optional[ConversationState]:
        """
        Restore state from a specific turn number.
        
        Args:
            turn_number: The turn number to restore from
            
        Returns:
            The restored state or None if not found
        """
        if turn_number in self.state_history:
            self.current_state = ConversationState.from_dict(self.state_history[turn_number])
            return self.current_state
        return None

    def get_current_state(self) -> ConversationState:
        """Get the current conversation state."""
        return self.current_state

    def clear_state_history(self) -> None:
        """Clear the state history and reset current state."""
        self.state_history.clear()
        self.current_state = ConversationState()

    def start(self, messages: Dict[str, str]) -> None:
        """
        Start the conversation with required messages.
        
        Args:
            messages: Dictionary containing 'system' and 'user' messages
            
        Raises:
            ValueError: If required messages are missing
        """
        if not messages or 'system' not in messages or 'user' not in messages:
            raise ValueError("Both system and user messages are required")
            
        import asyncio
        try:
            asyncio.run(self._run_conversation(messages['system'], messages['user']))
        except KeyboardInterrupt:
            print("\nExiting...")
        finally:
            self.display.terminal.reset()

    async def _run_conversation(self, system_msg: str, intro_msg: str):
        """
        Run the conversation loop with initial messages.
        
        Args:
            system_msg: System prompt for conversation context
            intro_msg: Initial user message
        """
        try:
            self.current_state.system_prompt = system_msg
            _, intro_styled, _ = await self.handle_intro(intro_msg)
            
            while True:
                user_input = await self.terminal.get_user_input()
                if not user_input:
                    continue
                    
                cmd = user_input.lower().strip()
                if cmd in ["edit", "retry"]:
                    _, intro_styled, _ = await self.handle_edit_or_retry(
                        intro_styled, 
                        is_retry=cmd=="retry"
                    )
                else:
                    _, intro_styled, _ = await self.handle_message(
                        user_input, 
                        intro_styled
                    )
        except Exception as e:
            self.logger.error(f"Critical error: {str(e)}", exc_info=True)
            raise
        finally:
            await self.io.update_display()

    async def _process_message(self, msg: str, silent: bool = False) -> Tuple[str, str]:
        """
        Process a user message and generate a response.
        
        Args:
            msg: User message to process
            silent: Whether to suppress loading animation
            
        Returns:
            Tuple of (raw_response, styled_response)
        """
        try:
            turn_number = self.current_state.turn_number + 1
            
            self.messages.append(Message("user", msg, turn_number))
            self.update_state(
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
                self.update_state(messages=await self.get_messages())
                
            return raw, styled
        except Exception as e:
            self.logger.error(f"Message processing error: {str(e)}", exc_info=True)
            return "", ""

    async def get_messages(self) -> List[Dict[str, str]]:
        """
        Get the current message history including system prompt if present.
        
        Returns:
            List of message dictionaries with role and content
        """
        base_messages = [{"role": m.role, "content": m.content} for m in self.messages]
        return ([{"role": "system", "content": self.current_state.system_prompt}] + base_messages
                if self.current_state.system_prompt else base_messages)

    async def _process_preface(self, text_list) -> str:
        """Process list of preface content into styled text."""
        if not text_list:
            return ""
        return ''.join([await self._format_preface_content(content) for content in text_list])

    async def _format_preface_content(self, content: PrefaceContent) -> str:
        """Format a single preface content item."""
        self.styles.set_output_color(content.color)
        strategy = self._display_strategies[content.display_type]
        _, styled = await self.styles.write_styled(strategy.format(content))
        return styled

    async def handle_intro(self, intro_msg: str) -> Tuple[str, str, str]:
        """
        Handle the initial message of the conversation.
        
        Args:
            intro_msg: Initial user message
            
        Returns:
            Tuple of (raw_response, styled_response, prompt)
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
        self.update_state(
            is_silent=True,
            prompt_display="",
            preconversation_styled=self.preconversation_styled
        )
        
        return raw, full_styled, ""

    async def handle_message(self, user_input: str, intro_styled: str) -> Tuple[str, str, str]:
        """
        Handle a user message during conversation.
        
        Args:
            user_input: User's message
            intro_styled: Previously styled content
            
        Returns:
            Tuple of (raw_response, styled_response, prompt)
        """
        await self.io.handle_scroll(intro_styled, f"> {user_input}", 0.08)
        raw, styled = await self._process_message(user_input)
        
        self.is_silent = False
        end_char = user_input[-1] if user_input.endswith(('?', '!')) else '.'
        self.prompt = f"> {user_input.rstrip('?.!')}{end_char * 3}"
        self.preconversation_styled = ""
        
        self.update_state(
            is_silent=False,
            prompt_display=self.prompt,
            preconversation_styled=""
        )
        
        return raw, styled, self.prompt

    async def handle_edit_or_retry(self, intro_styled: str, is_retry: bool = False) -> Tuple[str, str, str]:
        """
        Handle edit or retry commands.
        
        Args:
            intro_styled: Previously styled content
            is_retry: Whether this is a retry operation
            
        Returns:
            Tuple of (raw_response, styled_response, prompt)
        """
        current_turn = self.current_state.turn_number
        
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
            self.restore_state(current_turn - 1)
        
        if self.is_silent:
            raw, styled = await self._process_message(last_msg, silent=True)
            self.update_state(
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
        self.update_state(prompt_display=self.prompt)
        return raw, styled, self.prompt

    def preface(self, text: str, color: Optional[str] = None, display_type: str = "panel") -> None:
        """
        Add preface content to the conversation.
        
        Args:
            text: Content to display
            color: Optional color for the text
            display_type: Display style ("text" or "panel")
        """
        self.preconversation_text.append(PrefaceContent(text, color, display_type))
        self.update_state(preconversation_styled=self.preconversation_styled)