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
    """Container for preface content with display metadata."""
    text: str
    color: Optional[str]
    display_type: str = "text"  # "text" or "panel"

class DisplayStrategy(Protocol):
    """Protocol defining how content should be displayed."""
    def format(self, content: PrefaceContent) -> str: ...
    def get_visible_length(self, text: str) -> int: ...

class TextDisplayStrategy:
    """Original text display strategy."""
    def __init__(self, styles):
        self.styles = styles
    
    def format(self, content: PrefaceContent) -> str:
        return content.text + "\n"
        
    def get_visible_length(self, text: str) -> int:
        return self.styles.get_visible_length(text)

class PanelDisplayStrategy:
    """Rich panel display strategy."""
    def __init__(self, styles):
        self.styles = styles
        self.console = Console(
            force_terminal=True,
            color_system="truecolor", 
            record=True
        )
    
    def format(self, content: PrefaceContent) -> str:
        with self.console.capture() as capture:
            self.console.print(Panel(
                content.text.rstrip(),
                style=content.color or ""
            ))
        return capture.get()  # Rich handles newlines, don't add our own
        
    def get_visible_length(self, text: str) -> int:
        # Account for panel borders in length calculation
        return self.styles.get_visible_length(text) + 4

class Conversation:
    @staticmethod
    def get_default_messages() -> Tuple[str, str]:
        """Get the default system and intro messages.
        
        Returns:
            Tuple[str, str]: (system_message, intro_message)
        """
        return (
            'Be helpful, concise, and honest. Use text styles:\n'
            '- "quotes" for dialogue\n'
            '- [brackets] for observations\n'
            '- underscores for emphasis\n'
            '- asterisks for bold text',
            "Introduce yourself in 3 lines, 7 words each..."
        )

    def __init__(self, terminal, generator_func: Any, styles, stream, 
                 animations_manager, system_prompt: str = None):
        self.terminal = terminal
        self.generator = generator_func
        self.styles = styles
        self.stream = stream
        self.animations = animations_manager
        self.messages: List[Message] = []
        self.is_silent = False
        self.prompt = ""
        self.system_prompt = system_prompt
        self.preconversation_styled = ""
        self.preconversation_text: List[PrefaceContent] = []
        
        # Initialize display strategies
        self._display_strategies = {
            "text": TextDisplayStrategy(styles),
            "panel": PanelDisplayStrategy(styles)
        }

    def preface(self, text: str, color: Optional[str] = None,
                display_type: str = "panel") -> None:
        """Store text to be displayed before conversation starts.
        
        Args:
            text: The text to display before the conversation begins
            color: Optional color name (e.g., 'GREEN', 'BLUE', 'PINK').
            display_type: Display strategy to use ("text" or "panel")
        """
        content = PrefaceContent(
            text=text,
            color=color,
            display_type=display_type
        )
        self.preconversation_text.append(content)

    def start(self, system_msg: str = None, intro_msg: str = None) -> None:
        """Start the conversation with optional custom system and intro messages.
        
        Args:
            system_msg: Optional custom system message to override default
            intro_msg: Optional custom intro message to override default
        """
        self.run_conversation(
            system_msg=system_msg,
            intro_msg=intro_msg,
            preconversation_text=self.preconversation_text
        )

    def _get_last_user_message(self) -> Optional[str]:
        """Helper method to find the last user message in the conversation."""
        return next((m.content for m in reversed(self.messages) if m.role == "user"), None)

    async def get_messages(self) -> List[Dict[str, str]]:
        return (
            [{"role": "system", "content": self.system_prompt}] if self.system_prompt else []
        ) + [
            {"role": m.role, "content": m.content}
            for m in self.messages
        ]

    async def _process_message(self, msg: str, silent=False) -> Tuple[str, str]:
        """Process a user message with the AI generator, returning (raw, styled)."""
        self.messages.append(Message("user", msg))
        
        # Set green color for AI responses
        self.stream.set_base_color('GREEN')
        
        raw, styled = await self.animations.create_dot_loader(
            prompt="" if silent else f"> {msg}",
            output_handler=self.stream,
            no_animation=silent
        ).run_with_loading(self.generator(await self.get_messages()))
        
        self.messages.append(Message("assistant", raw))
        return raw, styled

    async def _process_preconversation_text(self, text_list: List[PrefaceContent]) -> str:
        """Process preconversation text with styling."""
        if not text_list:
            return ""
            
        styled_output = ""
        for content in text_list:
            # Set color or reset to default for preconversation text
            self.stream.set_base_color(content.color)
            
            # Get the appropriate display strategy
            strategy = self._display_strategies[content.display_type]
            
            # Format using selected strategy
            formatted = strategy.format(content)
            raw, new_styled = await self.stream.add(formatted)
            styled_output += new_styled
            
        return styled_output

    async def handle_intro(self, intro_msg: str,
                           preconversation_text: List[PrefaceContent] = None
                          ) -> Tuple[str, str, str]:
        """Process and display the intro message, showing preconversation text first if it exists."""
        # 1) Process the preface text (e.g. panel)
        self.preconversation_styled = await self._process_preconversation_text(preconversation_text)

        # 2) Display the preface text immediately (panel)
        if self.preconversation_styled.strip():
            # Force an extra blank line right after the panel so it appears from the start
            panel_with_blank = self.preconversation_styled.rstrip('\n') + '\n\n'
            await self.terminal.update_display(panel_with_blank, preserve_cursor=True)
        else:
            panel_with_blank = ""

        # 3) Now process the AI intro text in silent mode (no streaming displayed)
        raw, styled = await self._process_message(intro_msg, True)

        # 4) Combine so we have them for future scroll or display calls
        full_styled = panel_with_blank + styled

        # 5) If you want to display the final combined text right away:
        await self.terminal.update_display(full_styled)

        self.is_silent = True
        self.prompt = ""
        return raw, full_styled, ""

    async def handle_message(self, user_input: str, intro_styled: str) -> Tuple[str, str, str]:
        """Handle a user's message, scrolling the stored intro + user input up the screen."""
        # Scroll everything (panel + blank line + AI intro) with user input
        await self.terminal.handle_scroll(intro_styled, f"> {user_input}", 0.08)
        
        # Now process the new message normally (with streaming if not silent)
        raw, styled = await self._process_message(user_input)
        self.is_silent = False
        
        # Reconstruct the prompt
        end_char = '.' if not user_input.endswith(('?', '!')) else user_input[-1]
        self.prompt = f"> {user_input.rstrip('?.!')}{end_char * 3}"
        
        # After first user interaction, we clear out the preconversation text from memory
        self.preconversation_styled = ""
        
        # For future scrolls, only show new assistant reply
        full_styled = styled
        return raw, full_styled, self.prompt

    async def handle_edit_or_retry(self, intro_styled: str, is_retry: bool = False) -> Tuple[str, str, str]:
        """Handle both edit and retry commands using shared reverse streaming logic."""
        # Create reverse streamer with knowledge of preconversation text
        reverse_streamer = self.animations.create_reverse_streamer()
        await reverse_streamer.reverse_stream(
            intro_styled,
            "" if self.is_silent else self.prompt,
            preconversation_text=self.preconversation_styled
        )
        
        if self.is_silent:
            # If still silent (e.g. no user input was processed yet)
            if last_msg := self._get_last_user_message():
                raw, styled = await self._process_message(last_msg, True)
                # Preserve the blank line if you want
                full_styled = f"{self.preconversation_styled}\n{styled}"
                return raw, full_styled, ""
        else:
            last_msg = self._get_last_user_message()
            if last_msg:
                if is_retry:
                    # For retry, reprocess the last user message
                    await self.terminal.clear()
                    raw, styled = await self._process_message(last_msg)
                    
                    # Rebuild prompt
                    end_char = '.' if not last_msg.endswith(('?', '!')) else last_msg[-1]
                    self.prompt = f"> {last_msg.rstrip('?.!')}{end_char * 3}"
                    
                    # Insert the extra newline for consistency
                    full_styled = f"{self.preconversation_styled}\n{styled}"
                    return raw, full_styled, self.prompt
                else:
                    # For edit, prompt user for the new message with old content pre-filled
                    if msg := await self.terminal.get_user_input(last_msg, False):
                        await self.terminal.clear()
                        raw, styled = await self._process_message(msg)
                        
                        end_char = '.' if not msg.endswith(('?', '!')) else msg[-1]
                        self.prompt = f"> {msg.rstrip('?.!')}{end_char * 3}"
                        
                        # Insert the extra newline if desired
                        full_styled = f"{self.preconversation_styled}\n{styled}"
                        return raw, full_styled, self.prompt

        return "", "", ""

    async def handle_edit(self, intro_styled: str) -> Tuple[str, str, str]:
        """Handle the edit command."""
        return await self.handle_edit_or_retry(intro_styled, is_retry=False)

    async def handle_retry(self, intro_styled: str) -> Tuple[str, str, str]:
        """Handle the retry command."""
        return await self.handle_edit_or_retry(intro_styled, is_retry=True)

    def run_conversation(self, system_msg: str = None, intro_msg: str = None,
                        preconversation_text: List[PrefaceContent] = None):
        """Synchronous entry point that sets up asyncio."""
        import asyncio
        asyncio.run(self._run_conversation(system_msg, intro_msg, preconversation_text))

    async def _run_conversation(self, system_msg: str = None, intro_msg: str = None,
                              preconversation_text: List[PrefaceContent] = None):
        """Internal async implementation of the conversation loop"""
        try:
            # Use defaults if none provided
            if system_msg is None or intro_msg is None:
                system_msg, intro_msg = self.get_default_messages()
            
            self.system_prompt = system_msg
            _, intro_styled, _ = await self.handle_intro(intro_msg, preconversation_text)
            
            while True:
                if user := await self.terminal.get_user_input():
                    try:
                        if user.lower() == "edit":
                            _, intro_styled, _ = await self.handle_edit(intro_styled)
                        elif user.lower() == "retry":
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
