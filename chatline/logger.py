# logger.py

import sys
import logging
import os
import json
from typing import Optional
from functools import partial

class Logger:
    """
    Custom logger that supports both standard logs
    and optional JSON conversation history logs.
    """

    def __init__(self, name: str, logging_enabled: bool = False, log_file: Optional[str] = None):
        """
        Args:
            name: The logger name.
            logging_enabled: If True, standard logging is turned on.
            log_file: If "-", logs go to stdout;
                      If None, logs go nowhere;
                      Otherwise logs go to the given file path.
        """
        self._logger = logging.getLogger(name)
        self._logger.propagate = False
        
        # Clear any existing handlers
        self._logger.handlers.clear()
        
        self.logging_enabled = logging_enabled
        self.log_file = log_file
        self.json_history_path = None

        # Standard logging setup
        if logging_enabled:
            # Decide how to log text-based messages
            if log_file == '-':
                handler = logging.StreamHandler(sys.stdout)
            elif log_file:
                # Create directory for log file if it doesn't exist
                log_dir = os.path.dirname(log_file)
                if log_dir:
                    os.makedirs(log_dir, exist_ok=True)
                handler = logging.FileHandler(log_file, mode='w')
            else:
                handler = logging.StreamHandler(sys.stderr)
            
            handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            
            self._logger.addHandler(handler)
            self._logger.setLevel(logging.DEBUG)

            # For conversation JSON logs, use a single file "conversation_history.json"
            # in the same directory as log_file (if it's not "-" or None).
            if log_file and log_file not in ("-", ""):
                log_dir = os.path.dirname(log_file) or "."
                os.makedirs(log_dir, exist_ok=True)
                # Always overwrite the same file each run
                self.json_history_path = os.path.join(log_dir, "conversation_history.json")
        else:
            # If logging is disabled, a NullHandler swallows logs
            self._logger.addHandler(logging.NullHandler())

        # Expose convenience methods like self.debug, self.info, self.error, ...
        for level in ['debug', 'info', 'warning', 'error']:
            setattr(self, level, partial(self._log, level))

    def _log(self, level: str, msg: str, exc_info: Optional[bool] = None) -> None:
        getattr(self._logger, level)(msg, exc_info=exc_info)

    def write_json(self, data):
        """
        Overwrite the entire conversation JSON file with 'data' each time.
        If self.json_history_path is None, do nothing.
        """
        if not self.json_history_path:
            return
        try:
            with open(self.json_history_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            self.error(f"Failed to write JSON history: {e}")