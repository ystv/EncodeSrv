""" Module to handle setting up logging.

Author: Robert Walker <robert.walker@ystv.co.uk> 2015
"""

import logging.handlers
from . import bots

from ..config import Config

LOG_FILENAME= "/tmp/encodesrv.log"
LOG_FORMAT = '%(asctime)s:%(name)s:%(levelname)s:%(message)s'

def setup_logging(encodesrv):
    
    """Make all the log handlers set the log formats.
    
    Arguments:
        None.
        
    Returns:
        '__main__' logger.
    """
    
    logging.basicConfig(filename = LOG_FILENAME, level = logging.DEBUG, format = LOG_FORMAT)
    
    streamhandler = logging.StreamHandler()
    streamhandler.setFormatter(logging.Formatter(LOG_FORMAT))
    logging.getLogger().addHandler(streamhandler)

    # Setup logging to email for critical failures
    mailhandler = logging.handlers.SMTPHandler(mailhost=Config["mail"]["host"],
                            fromaddr=Config["mail"]["from"],
                            toaddrs=Config["mail"]["to"],
                            subject='Encode Job Failure')
    mailhandler.setLevel(logging.ERROR)
    ##logging.getLogger('').addHandler(mailhandler)
    
    # Slack bot logging
    if Config['slack']['enabled']:
        bots.get_bot('slack', encodesrv, **Config['slack'])

    # IRC bot logging
    if Config['irc']['enabled']:
        bots.get_bot('irc', encodesrv, **Config['irc'])

    return logging.getLogger('__main__')