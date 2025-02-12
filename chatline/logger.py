import os, logging
from typing import Optional
from functools import partial

class Logger:
    def __init__(self, name: str, logging_enabled: bool = False):
        self._logger = logging.getLogger(name)
        if logging_enabled:
            project_root = os.path.dirname(os.path.dirname(__file__))
            os.makedirs(os.path.join(project_root, 'logs'), exist_ok=True)
            logging.basicConfig(level=logging.DEBUG,
                              format='%(asctime)s - %(levelname)s - %(message)s',
                              filename=os.path.join(project_root, 'logs', 'chat_debug.log'))
        else:
            self._logger.addHandler(logging.NullHandler())

        # Dynamically create logging methods
        for level in ['debug', 'info', 'warning', 'error']:
            setattr(self, level, partial(self._log, level))

    def _log(self, level: str, msg: str, exc_info: Optional[bool] = None) -> None:
        getattr(self._logger, level)(msg, exc_info=exc_info)