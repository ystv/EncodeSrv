_bots = []


def get_bot(bot, *args, **kwargs):
    
    if bot == 'irc_':
        from . import irc_
        return_bot = irc_.Encode_irc(*args, **kwargs)
    elif bot == 'slack':
        from . import slack
        return_bot = slack.Encode_slack(*args, **kwargs)
        
    _bots.append(return_bot)
    return return_bot
    
