"""Stuff common to all the bot handlers.

Author: Robert Walker <robert.walker@ystv.co.uk> 2015
"""

import re

privmsg_re = re.compile(r"^<?@?([^ |^>]*)>?: *(.*)")
"""Regex to pull the user and message from slack/IRC strings."""

def form_status_msg():
    
    """Form a nice, human readable message for the status of the server.
    
    Arguments:
        None.
        
    Returns:
        Status message (string).
    """
    
    return "Currently encoding <things>, with <some> items waiting."