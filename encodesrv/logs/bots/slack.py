"""Slack bot handler for encodesrv.

Author: Robert Walker <robert.walker@ystv.co.uk> 2015
"""

import logging
import Queue as queue
import slackclient
import threading
import time

from . import common
from ...config import Config
from ..messages import Message_enum

logger = logging.getLogger(__name__)

class Slack_rtm_thread(threading.Thread):
    
    def __init__(self, parent, api_key, send_queue):
        
        super(Slack_rtm_thread, self).__init__(daemon = True)
        self.api_key = api_key
        self.send_queue = send_queue
        self.channel = None
        self.parent = parent
        self.connected = False
        
    def get_connected(self):
        
        return self.connected
        
    def get_channel(self):
        
        return self.channel
    
    def set_channel(self, channel):
        
        self.channel = channel
        
    def run(self):
        self.slackclient = slackclient.SlackClient(self.api_key)
        connect = self.slackclient.rtm_connect()
        if connect:
            self.connected = True
            self.id = self.slackclient.server.users.find(self.slackclient.server.username)
            while True:
                try:
                    msg = self.send_queue.get(block = False)
                    self.slackclient.rtm_send_message(self.get_channel(), Config["servername"] + "> " + msg)
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
        else:
            raise Exception("Could not connect to Slack.")
    
    def _slack_respond(self, msg):
        
        matches = common.privmsg_re.findall(msg['text'])
        if len(matches) != 1:
            return
        user, cmd = matches[0]
        if user == self.slackclient.server.username or user == self.id:
            daemon = self.parent.parent
            enum = Message_enum
            form_msg = common.form_msg
    
            if cmd == "status":
                msg = form_msg(enum.status, daemon)
            else:
                msg = form_msg(enum.unknown_cmd, daemon)
            
            self.send_queue.put(msg)
        
    def __str__(self):
        
        return str(self.slackclient)
        

class Encode_slack():
    
    def __init__(self, parent, api_key = None, channel = None, **kwargs):
        
        assert type(api_key) == str
        self.send_queue = queue.Queue()
        self.rtm_thread = Slack_rtm_thread(self, api_key, self.send_queue)
        self.rtm_thread.start()
        self.parent = parent
        if channel is not None:
            self.set_channel(channel)
        while not self.rtm_thread.get_connected():
            time.sleep(0.1)
        logger.info("Connected to Slack.")
    
    def get_channel(self):
        
        return self.rtm_thread.get_channel()
    
    def set_channel(self, channel):
        
        self.rtm_thread.set_channel(channel)
        
    def send_msg(self, msg):
        
        self.send_queue.put(msg)
        
    def emit(self, record):

        self.send_msg(record.getMessage())    
