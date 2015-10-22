from . import irc
from . import slack


_bots = []


def get_bot(bot, *args, **kwargs):
    
    if bot == 'irc':
        return_bot = irc.Encode_irc(*args, **kwargs)
    elif bot == 'slack':
        return_bot = slack.Encode_slack(*args, **kwargs)
        
    _bots.append(return_bot)
    return return_bot
    