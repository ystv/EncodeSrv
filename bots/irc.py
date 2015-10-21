import irc.bot
import irc.strings
import logging
import threading

logging.getLogger('irc').setLevel(logging.CRITICAL)

class IRC_bot(irc.bot.SingleServerIRCBot):
    
    def __init__(self, channel, nickname, server, port=6667):
        irc.bot.SingleServerIRCBot.__init__(self, [(server, port)], nickname, nickname)
        self.channel = channel
        self.joined = False
        
    def _on_join(self, c, e):
        super(IRC_bot, self)._on_join(c, e)
        self.joined = True

    def on_nicknameinuse(self, c, e):
        c.nick(c.get_nickname() + "_")

    def on_welcome(self, c, e):
        c.join(self.channel)

    def on_privmsg(self, c, e):
        self.do_command(e, e.arguments[0], True)

    def on_pubmsg(self, c, e):
        a = e.arguments[0].split(":", 1)
        if len(a) > 1 and irc.strings.lower(a[0]) == irc.strings.lower(self.connection.get_nickname()):
            self.do_command(e, a[1].strip())
        return

    def do_command(self, e, cmd, private = False):
        nick = e.source.nick

        if cmd == "status":
            msg = "Currently encoding <things>, with <some> items waiting."
        else:
            msg = "Unknown command."
            
        if private:
            args = {"msg": msg, "channel": nick}
        else:
            args = {"msg": nick + ": " + msg}
        
        self.send_msg(**args)
            
    def is_joined(self):
        
        return self.joined
    
    def send_msg(self, msg = "", channel = None):
        
        if channel is None:
            channel = self.channel
        self.connection.privmsg(channel, msg)

class Bot_thread(threading.Thread):
    
    def __init__(self, bot):
        
        super(Bot_thread, self).__init__()
        self.bot = bot
        
    def run(self):
        
        self.bot.start()

class Encode_irc(logging.Handler):
    
    def __init__(self, server = None, port = 6667, channel = None, nick = None, **kwargs):
        
        super(Encode_irc, self).__init__()
        self.bot = IRC_bot(channel, nick, server, port)
        self.thread = Bot_thread(self.bot)
        self.thread.start()
    
    def is_joined(self):
        
        return self.bot.is_joined()
        
    def emit(self, record):
        
        self.send_msg(record.getMessage())
        
    def send_msg(self, msg):
        
        self.bot.send_msg(msg)