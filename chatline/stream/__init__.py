# stream/__init__.py

from typing import Optional, Callable
from .embedded import EmbeddedStream
from .remote import RemoteStream

class Stream:
    """Base class for handling message streaming."""
    
    def __init__(self, logger=None):
        self.logger = logger
        self._last_error: Optional[str] = None

    @classmethod 
    def create(cls, endpoint: Optional[str] = None, logger=None, generator_func=None) -> 'Stream':
        if endpoint:
            return RemoteStream(endpoint, logger=logger)
        return EmbeddedStream(logger=logger, generator_func=generator_func)

    def get_generator(self) -> Callable:
        raise NotImplementedError

__all__ = ['Stream']