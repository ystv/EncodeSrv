""" Module to handle setting up logging.

Author: Robert Walker <robert.walker@ystv.co.uk> 2015
"""

import logging.handlers
from .bots import slack
from .bots import irc

from .config import Config

LOG_FILENAME= "/tmp/encodesrv.log"
LOG_FORMAT = '%(asctime)s:%(levelname)s:%(message)s'

def setup_logging(encodesrv_daemon):
    
    """Make all the log handlers set the log formats.
    
    Arguments:
        None.
        
    Returns:
        '__main__' logger.
    """
    
    logging.basicConfig(filename = LOG_FILENAME, level = logging.DEBUG, format = LOG_FORMAT)

    # Setup logging to email for critical failures
    mailhandler = logging.handlers.SMTPHandler(mailhost=Config["mail"]["host"],
                            fromaddr=Config["mail"]["from"],
                            toaddrs=Config["mail"]["to"],
                            subject='Encode Job Failure')
    mailhandler.setLevel(logging.ERROR)
    ##logging.getLogger('').addHandler(mailhandler)
    
    # Slack bot logging
    if Config['slack']['enabled']:
        slackhandler = slack.Encode_slack(encodesrv_daemon, **Config['slack'])
        slackhandler.setLevel(logging.INFO)
        logging.getLogger().addHandler(slackhandler)

    # IRC bot logging
    if Config['irc']['enabled']:
        irchandler = irc.Encode_irc(encodesrv_daemon, **Config['irc'])
        
        while not irchandler.is_joined():
            pass
        irchandler.setLevel(logging.INFO)
        logging.getLogger().addHandler(irchandler)

    return logging.getLogger('__main__')