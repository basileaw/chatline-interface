# interface.py

import logging
import os
from .terminal import Terminal
from .conversation import Conversation
from .animations import Animations
from .styles import Styles
from .stream import EmbeddedStream, RemoteStream
from .generator import generate_stream

class Interface:
    def __init__(self, endpoint=None, generator_func=None):
        self._setup_logging()
        if not endpoint and not generator_func:
            generator_func = generate_stream
        self._init_components(endpoint, generator_func)

    def _setup_logging(self):
        log_dir = os.path.join(os.path.dirname(__file__), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s',
            filename=os.path.join(log_dir, 'chat_debug.log')
        )
        self.logger = logging.getLogger(__name__)

    def _init_components(self, endpoint, generator_func):
        try:
            # Terminal and styles initialization
            self.terminal = Terminal(styles=None)
            self.styles = Styles(terminal=self.terminal)
            self.terminal.styles = self.styles
            
            # Animations setup
            self.animations = Animations(
                terminal=self.terminal,
                styles=self.styles
            )
            
            # Stream initialization
            if endpoint:
                self.logger.info("Using remote endpoint: %s", endpoint)
                self.stream = RemoteStream(endpoint, logger=self.logger)
            else:
                self.logger.info("Using embedded stream")
                self.stream = EmbeddedStream(generator_func, logger=self.logger)
                
            self.generator = self.stream.get_generator()
            
            # Conversation setup
            self.conversation = Conversation(
                terminal=self.terminal,
                generator_func=self.generator,
                styles=self.styles,
                animations_manager=self.animations
            )
            
            self.terminal._clear_screen()
            self.terminal._hide_cursor()
            
        except Exception as e:
            self.logger.error("Init error: %s", str(e))
            raise

    def preface(self, text, color=None, display_type="panel"):
        try:
            self.conversation.preface(text, color, display_type)
            self.logger.debug("Added preface: %s", text[:50])
        except Exception as e:
            self.logger.error("Preface error: %s", str(e))
            raise

    def start(self, system_msg=None, intro_msg=None):
        try:
            self.conversation.start(system_msg, intro_msg)
        except KeyboardInterrupt:
            self.logger.info("User interrupted")
            self.terminal._show_cursor()
        except Exception as e:
            self.logger.error("Start error: %s", str(e))
            self.terminal._show_cursor()
            raise