# adaptive_buffer.py

import time
import asyncio
from typing import Tuple, Any

class AdaptiveBuffer:
    """
    A buffer that adaptively manages the flow of text chunks based on timing.
    Provides smooth output by adjusting release intervals based on input rate.
    """
    
    def __init__(self, window_size: int = 15):
        """
        Initialize the adaptive buffer.
        
        Args:
            window_size (int): Size of the sliding window for timing calculations
        """
        self.buf = []  # Buffer for text chunks
        self.times = []  # Timestamps of chunk arrivals
        self.wsize = window_size  # Window size for timing calculations
        self.last_rel = time.time()  # Time of last chunk release
    
    def calc_interval(self) -> float:
        """
        Calculate the ideal interval between chunk releases based on input timing.
        Uses a sliding window of recent intervals to adapt to changing input rates.
        
        Returns:
            float: Calculated interval in seconds
        """
        if len(self.times) < 2:
            return 0.08  # Default interval for insufficient data
            
        # Calculate intervals between recent chunks
        intervals = [t2 - t1 for t1, t2 in zip(self.times[-self.wsize:], 
                                             self.times[-self.wsize+1:])]
        
        # If no valid intervals, use default
        if not intervals:
            return 0.08
            
        # Calculate adaptive interval as half the average interval
        return (sum(intervals) / len(intervals)) * 0.5

    async def add(self, chunk: str, output_handler: Any) -> Tuple[str, str]:
        """
        Add a new chunk to the buffer and potentially release some chunks.
        
        Args:
            chunk: Text chunk to add
            output_handler: Handler to process chunks when releasing
            
        Returns:
            Tuple[str, str]: Accumulated raw and styled output from any released chunks
        """
        now = time.time()
        self.buf.append(chunk)
        self.times.append(now)
        
        # Keep timing window from growing too large
        if len(self.times) > self.wsize * 2:
            self.times = self.times[-self.wsize:]
            
        # Release chunks if buffer is getting full
        if len(self.buf) > self.wsize:
            return await self.release_some(output_handler)
            
        return "", ""

    async def release_some(self, output_handler: Any) -> Tuple[str, str]:
        """
        Release chunks from the buffer based on timing.
        
        Args:
            output_handler: Handler to process released chunks
            
        Returns:
            Tuple[str, str]: Accumulated raw and styled output from released chunks
        """
        interval = self.calc_interval()
        raw_acc, style_acc = "", ""
        
        while self.buf and (time.time() - self.last_rel) >= interval:
            chunk = self.buf.pop(0)
            raw, styled = output_handler.process_and_write(chunk)
            raw_acc += raw
            style_acc += styled
            self.last_rel = time.time()
            await asyncio.sleep(0)  # Allow other tasks to run
            
        return raw_acc, style_acc

    async def flush(self, output_handler: Any) -> Tuple[str, str]:
        """
        Flush all remaining chunks from the buffer.
        
        Args:
            output_handler: Handler to process chunks
            
        Returns:
            Tuple[str, str]: Accumulated raw and styled output from all chunks
        """
        raw_total, style_total = "", ""
        
        while self.buf:
            raw, styled = await self.release_some(output_handler)
            raw_total += raw
            style_total += styled
            if not self.buf:
                break
                
        return raw_total, style_total