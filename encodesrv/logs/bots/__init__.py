from encodesrv.logs.bots import irc_
from . import slack


_bots = []


def get_bot(bot, *args, **kwargs):
    
    if bot == 'irc_':
        return_bot = irc_.Encode_irc(*args, **kwargs)
    elif bot == 'slack':
        return_bot = slack.Encode_slack(*args, **kwargs)
        
    _bots.append(return_bot)
    return return_bot
    