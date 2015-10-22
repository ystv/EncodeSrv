"""Stuff common to all the bot handlers.

Author: Robert Walker <robert.walker@ystv.co.uk> 2015
"""

import re
import psycopg2
import enum
from ...config import Config

privmsg_re = re.compile(r"^<?@?([^ |^>]*)>?: *(.*)")
"""Regex to pull the user and message from Slack/IRC strings."""

class Message_enum(enum.Enum):
    
    status = 1
    unknown_cmd = 2
    start_job = 3
    finish_job = 4
    

message_dict = {
                Message_enum.status: "Currently encoding {}, with {} item{} waiting.",
                Message_enum.unknown_cmd: "I don't know what you're asking.",
                Message_enum.start_job: "Starting job {id_}: {name}.",
                Message_enum.finish_job: "Finished job {id_}: {name}."
                }


def form_msg(enum_value, encodesrv_daemon = None):
    
    """Form whatever message is required.
    
    Arguments:
        enum_value (Message_enum): The enum value related to the requested message.
        encodesrv_daemon (EncodeSrvDaemon): Main encodesrv instance.
    
    Returns:
        Message (string).
    """
    
    if enum_value == Message_enum.status:
        assert encodesrv_daemon != None
        return form_status_msg(encodesrv_daemon)
    elif enum_value == Message_enum.unknown_cmd:
        return form_help_msg()


def form_help_msg():
    
    """Form a nice, human readable, help message for the bot.
    
    Arguments:
        None.
        
    Returns:
        Help message (string).
    """
    
    return message_dict[Message_enum.unknown_cmd]


def form_status_msg(encodesrv_daemon):
    
    """Form a nice, human readable message for the status of the server.
    
    Arguments:
        None.
        
    Returns:
        Status message (string).
    """
    
    encoding = encodesrv_daemon.get_current_jobs()
    
    if encoding == []:
        encoding = 'no jobs'
    else:
        encoding = ', '.join(encoding).rstrip(', ')
        
    dbconn = psycopg2.connect(**Config["database"])
    cur = dbconn.cursor()
    cur.execute("SELECT COUNT(*) FROM encode_jobs WHERE status ='Not Encoding' or status = 'Waiting'")
    waiting = cur.fetchone()[0]
    cur.close()
    dbconn.close()
    
    return message_dict[Message_enum.status].format(encoding, waiting, "" if int(waiting) == 1 else "s" )
