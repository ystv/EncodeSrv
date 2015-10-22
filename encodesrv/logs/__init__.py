"""Package to deal with the various bits of logging for encodesrv"""


import logging
from . import bots
from . import messages


def get_logger(name):
    
    """Function for other modules to get the correct logger.
    TODO: Make proper factory/singleton thing.
    """
    
    return Logger(name)


class Logger():
    
    """Wrapper around logging.Logger class, so bots can receive stuff."""
    
    def __init__(self, name):
    
        self._logger = logging.getLogger(name)
        
    def _bot_emit(self, msg, bot_data = None):
        
        for bot in bots._bots:
            bot.send_msg(msg)
        
    def _msg_fmt(self, msg, data = None):
        
        if type(msg) == messages.Message_enum:
            msg = messages.message_dict[msg]
            if data is not None:
                msg = msg.format(**data)
        return msg
        
    def info(self, msg, data = None, bot = True):
        
        msg = self._msg_fmt(msg, data)
        self._logger.info(msg)
        if bot:
            self._bot_emit(msg, data)
        
    def debug(self, msg, data = None, bot = True):
        
        msg = self._msg_fmt(msg, data)
        self._logger.debug(msg)
        
    def error(self, msg, data = None, bot = True):
        
        msg = self._msg_fmt(msg, data)
        self._logger.error(msg)
        if bot:
            self._bot_emit(msg, data)
        
    def exception(self, msg, data = None, bot = True):
        
        msg = self._msg_fmt(msg, data)
        self._logger.exception(msg)
        if bot:
            self._bot_emit(msg, data)
    
    def critical(self, msg, data = None, bot = True):
        
        msg = self._msg_fmt(msg, data)
        self._logger.critical(msg)
        if bot:
            self._bot_emit(msg, data)