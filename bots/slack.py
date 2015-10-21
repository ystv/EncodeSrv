import logging
import queue
import slackclient
import threading
import time

from . import common

logger = logging.getLogger(__name__)

class Slack_rtm_thread(threading.Thread):
    
    def __init__(self, parent, api_key, send_queue):
        
        super(Slack_rtm_thread, self).__init__(daemon = True)
        self.api_key = api_key
        self.send_queue = send_queue
        self.channel = None
        self.parent = parent
        
    def get_channel(self):
        
        return self.channel
    
    def set_channel(self, channel):
        
        self.channel = channel
        
    def run(self):
        self.slackclient = slackclient.SlackClient(self.api_key)
        if self.slackclient.rtm_connect():
            self.id = self.slackclient.server.users.find(self.slackclient.server.username)
            while True:
                try:
                    msg = self.send_queue.get(block = False)
                    self.slackclient.rtm_send_message(self.get_channel(), msg)
                except queue.Empty:
                    responses = self.slackclient.rtm_read()
                    if responses == []:
                        continue
                    for msg in responses:
                        try:
                            if msg['type'] == 'message':
                                self._slack_respond(msg)
                        except KeyError:
                            continue
                finally:
                    time.sleep(0.1)
    
    def _slack_respond(self, msg):
        
        matches = common.privmsg_re.findall(msg['text'])
        if len(matches) != 1:
            return
        user, cmd = matches[0]
        if user == self.slackclient.server.username or user == self.id:
            daemon = self.parent.parent
            enum = common.Message_enum
            form_msg = common.form_msg
    
            if cmd == "status":
                msg = form_msg(enum.status, daemon)
            else:
                msg = form_msg(enum.unknown_cmd, daemon)
            
            self.send_queue.put(msg)
        
    def __str__(self):
        
        return str(self.slackclient)
        

class Encode_slack(logging.Handler):
    
    def __init__(self, parent, api_key = None, channel = None, **kwargs):
        super(Encode_slack, self).__init__()
        self.send_queue = queue.Queue()
        self.rtm_thread = Slack_rtm_thread(self, api_key, self.send_queue)
        self.rtm_thread.start()
        self.parent = parent
        if channel is not None:
            self.set_channel(channel)
    
    def get_channel(self):
        
        return self.rtm_thread.get_channel()
    
    def set_channel(self, channel):
        
        self.rtm_thread.set_channel(channel)
        
    def send_message(self, msg):
        
        self.send_queue.put(msg)
        
    def emit(self, record):

        self.send_message(record.getMessage())
        
if __name__ == '__main__':

    from time import sleep
    
    send_queue = queue.Queue()
    
    slackbot = Encode_slack("xoxb-12939465410-BNhRXRA5sqz67bd4w03eVoqV")
    slackbot.set_channel("firing_range")
    while True:
        sleep(10)
    
