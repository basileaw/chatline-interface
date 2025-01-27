# async_adaptive_buffer.py

import asyncio
import time
from typing import Tuple, Any, List

class AsyncAdaptiveBuffer:
    def __init__(self, window_size: int = 15):
        self._buffer: List[str] = []
        self._buffer_lock = asyncio.Lock()
        
    async def add(self, chunk: str, output_handler: Any) -> Tuple[str, str]:
        if not chunk:
            return "", ""
            
        # Process chunks immediately - don't try to be too clever with timing
        async with self._buffer_lock:
            raw, styled = output_handler.process_and_write(chunk)
            return raw, styled
            
    async def flush(self, output_handler: Any) -> Tuple[str, str]:
        return "", ""  # Nothing to flush since we process immediately
        
    def reset(self):
        pass  # No state to reset