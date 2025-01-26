# async_stream_manager.py

import asyncio
import time
from typing import Optional, Tuple, List, Any, Dict
from dataclasses import dataclass
from contextlib import asynccontextmanager

@dataclass
class StreamState:
    """Tracks the current state of the streaming process."""
    animation_complete: bool = False
    content_started: bool = False
    is_first_chunk: bool = True
    preserved_prompt: str = ""
    current_line_length: int = 0
    word_buffer: str = ""
    last_release_time: float = 0.0

class AsyncStreamManager:
    """
    Manages asynchronous streaming of content with animation coordination.
    Preserves word boundaries, handles proper spacing, and coordinates animations.
    """
    
    def __init__(self, text_painter: Any, window_size: int = 15):
        """
        Initialize the AsyncStreamManager.
        
        Args:
            text_painter: TextPainter instance for styling text
            window_size: Size of timing window for adaptive streaming
        """
        # Core async primitives
        self._animation_complete = asyncio.Event()
        self._content_ready = asyncio.Event()
        self._word_boundary_lock = asyncio.Lock()
        
        # State management
        self.state = StreamState()
        self.painter = text_painter
        self.window_size = window_size
        
        # Timing and buffering
        self.chunk_times: List[float] = []
        self.content_buffer: List[str] = []
        self.default_interval = 0.08
        
    @asynccontextmanager
    async def managed_cursor(self, show: bool):
        """Context manager for cursor visibility."""
        from utilities import manage_cursor
        try:
            manage_cursor(show)
            yield
        finally:
            manage_cursor(not show)
            
    async def calculate_adaptive_interval(self) -> float:
        """
        Calculate the ideal interval between chunk releases based on input timing.
        """
        if len(self.chunk_times) < 2:
            return self.default_interval
            
        intervals = [t2 - t1 for t1, t2 in zip(
            self.chunk_times[-self.window_size:], 
            self.chunk_times[-self.window_size+1:]
        )]
        
        if not intervals:
            return self.default_interval
            
        return (sum(intervals) / len(intervals)) * 0.5
        
    async def _animate_dots(self, prompt: str, interval: float = 0.4):
        """
        Handles the animated dots display.
        Maintains exact spacing and timing of the original implementation.
        """
        from utilities import write_and_flush
        
        async with self.managed_cursor(False):
            dots = 0
            while not self._animation_complete.is_set():
                # Clear line and write current state
                write_and_flush(f"\r{' '*80}\r{prompt}{'.'*dots}")
                
                if self.state.animation_complete and dots == 3:
                    # Preserve exact spacing behavior
                    if not self.state.preserved_prompt:
                        write_and_flush(f"\r{' '*80}\r{prompt}{'.'*3}\n\n")
                    else:
                        write_and_flush(f"\r{' '*80}\r{prompt}{'.'*3}\033[2B")
                    await asyncio.sleep(interval)
                    self._animation_complete.set()
                    break
                    
                # Update dot count
                if self.state.animation_complete:
                    dots = min(dots + 1, 3)
                else:
                    dots = (dots + 1) % 4
                    
                await asyncio.sleep(interval)
                
    async def process_word_buffer(self, output_handler: Any) -> Tuple[str, str]:
        """
        Process and clear the word buffer while preserving word boundaries.
        """
        async with self._word_boundary_lock:
            if not self.state.word_buffer:
                return "", ""
                
            raw, styled = output_handler.process_and_write(self.state.word_buffer)
            self.state.word_buffer = ""
            return raw, styled
            
    async def process_chunk(self, chunk: str, output_handler: Any) -> Tuple[str, str]:
        """
        Process a single chunk of content while preserving word boundaries.
        """
        if not chunk:
            return "", ""
            
        raw_acc, style_acc = "", ""
        
        async with self._word_boundary_lock:
            for char in chunk:
                if char.isspace():
                    if self.state.word_buffer:
                        raw, styled = await self.process_word_buffer(output_handler)
                        raw_acc += raw
                        style_acc += styled
                        
                    raw, styled = output_handler.process_and_write(char)
                    raw_acc += raw
                    style_acc += styled
                else:
                    self.state.word_buffer += char
                    
        return raw_acc, style_acc
        
    async def release_content(self, output_handler: Any) -> Tuple[str, str]:
        """
        Release buffered content while maintaining proper timing and word boundaries.
        """
        interval = await self.calculate_adaptive_interval()
        raw_acc, style_acc = "", ""
        
        while self.content_buffer and (
            time.time() - self.state.last_release_time >= interval
        ):
            chunk = self.content_buffer.pop(0)
            raw, styled = await self.process_chunk(chunk, output_handler)
            raw_acc += raw
            style_acc += styled
            self.state.last_release_time = time.time()
            await asyncio.sleep(0)
            
        return raw_acc, style_acc
        
    async def stream_content(
        self, 
        stream: Any,
        prompt: str,
        output_handler: Any,
        no_animation: bool = False
    ) -> Tuple[str, str]:
        """
        Main method for streaming content with animation coordination.
        
        Args:
            stream: Content stream to process
            prompt: Prompt text to display
            output_handler: Handler for processing output
            no_animation: Whether to disable animation
            
        Returns:
            Tuple[str, str]: Raw and styled accumulated output
        """
        raw_total, style_total = "", ""
        animation_task = None
        
        if not no_animation:
            animation_task = asyncio.create_task(
                self._animate_dots(prompt)
            )
            
        try:
            for chunk in stream:
                c = chunk.strip()
                if c == "data: [DONE]":
                    break
                    
                if c.startswith("data: "):
                    try:
                        import json
                        data = json.loads(c[6:])
                        text = data["choices"][0]["delta"].get("content", "")
                        
                        if text:
                            if self.state.is_first_chunk:
                                self.state.animation_complete = True
                                if not no_animation:
                                    await self._animation_complete.wait()
                                self.state.is_first_chunk = False
                                
                            now = time.time()
                            self.chunk_times.append(now)
                            if len(self.chunk_times) > self.window_size * 2:
                                self.chunk_times = self.chunk_times[-self.window_size:]
                                
                            self.content_buffer.append(text)
                            raw, styled = await self.release_content(output_handler)
                            raw_total += raw
                            style_total += styled
                            
                    except json.JSONDecodeError:
                        continue
                        
                await asyncio.sleep(0)
                
        finally:
            # Ensure animation is complete
            self.state.animation_complete = True
            if animation_task:
                await animation_task
                
            # Process any remaining content
            while self.content_buffer:
                raw, styled = await self.release_content(output_handler)
                raw_total += raw
                style_total += styled
                
            # Process final word buffer
            if self.state.word_buffer:
                raw, styled = await self.process_word_buffer(output_handler)
                raw_total += raw
                style_total += styled
                
            # Final output handler flush
            if hasattr(output_handler, 'flush'):
                final_styled = output_handler.flush()
                if final_styled:
                    style_total += final_styled
                    
        return raw_total, style_total