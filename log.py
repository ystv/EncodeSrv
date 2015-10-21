""" Module to handle setting up logging.

Author: Robert Walker <robert.walker@ystv.co.uk> 2015
"""

import logging.handlers
import bots.slack
import bots.irc

from config import Config

LOG_FILENAME= "encodesrv.log"
LOG_FORMAT = '%(asctime)s:%(levelname)s:%(message)s'

def setup_logging():
    
    """Make all the log handlers set the log formats.
    
    Arguments:
        None.
        
    Returns:
        '__main__' logger.
    """
    
    logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT)

    # Setup logging to email for critical failures
    mailhandler = logging.handlers.SMTPHandler(mailhost=Config["mail"]["host"],
                            fromaddr=Config["mail"]["from"],
                            toaddrs=Config["mail"]["to"],
                            subject='Encode Job Failure')
    mailhandler.setLevel(logging.ERROR)
    ##logging.getLogger('').addHandler(mailhandler)
    
    # Slack bot logging
    if Config['slack']['enabled']:
        slackhandler = bots.slack.Encode_slack(**Config['slack'])
        slackhandler.setLevel(logging.INFO)
        logging.getLogger().addHandler(slackhandler)

    # IRC bot logging
    if Config['irc']['enabled']:
        irchandler = bots.irc.Encode_irc(**Config['irc'])
        
        while not irchandler.is_joined():
            pass
        irchandler.setLevel(logging.INFO)
        logging.getLogger().addHandler(irchandler)

    return logging.getLogger('__main__')