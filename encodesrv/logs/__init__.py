"""Package to deal with the various bits of logging for encodesrv"""

import logging
from . import bots

def get_logger(name):
    
    """Function for other modules to get the correct logger.
    TODO: Make proper factory/singleton thing.
    """
    
    return Logger(name)

class Logger():
    
    """Wrapper around logging.Logger class, so bots can receive stuff."""
    
    def __init__(self, name):
    
        self._logger = logging.getLogger(name)
        
    def _bot_emit(self, msg):
        
        for bot in bots._bots:
            bot.send_msg(msg)
        
    def info(self, msg):
        
        self._logger.info(msg)
        self._bot_emit(msg)
        
    def debug(self, msg):
        
        self._logger.debug(msg)
        
    def error(self, msg):
        
        self._logger.error(msg)
        self._bot_emit(msg)
        
    def exception(self, msg):
        
        self._logger.exception(msg)
        self._bot_emit(msg)
    
    def critical(self, msg):
        
        self._logger.critical(msg)
        self._bot_emit(msg)