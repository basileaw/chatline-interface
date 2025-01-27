import asyncio
from typing import Tuple, Protocol

class OutputHandler(Protocol):
    def process_and_write(self, chunk: str) -> Tuple[str, str]: ...
    def flush(self) -> str | None: ...

class AsyncAdaptiveBuffer:
    """
    A simple async buffer for text processing.
    Processes chunks immediately to maintain smooth streaming.
    """
    def __init__(self, window_size: int = 15):
        self._buffer_lock = asyncio.Lock()
        
    async def add(self, chunk: str, output_handler: OutputHandler) -> Tuple[str, str]:
        """
        Process a chunk of text immediately.
        
        Args:
            chunk: Text to process
            output_handler: Handler for text output
            
        Returns:
            Tuple[str, str]: Raw and styled output
        """
        if not chunk:
            return "", ""
            
        # Process chunks immediately - no buffering needed
        async with self._buffer_lock:
            raw, styled = output_handler.process_and_write(chunk)
            return raw, styled
            
    async def flush(self, output_handler: OutputHandler) -> Tuple[str, str]:
        """
        Flush any remaining content.
        Since we process immediately, nothing to flush.
        
        Args:
            output_handler: Handler for text output
            
        Returns:
            Tuple[str, str]: Empty tuple since nothing to flush
        """
        return "", ""
        
    def reset(self):
        """Reset buffer state."""
        pass  # No state to reset