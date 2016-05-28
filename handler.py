#-------------------------------------------------------------------------------
# Name:        Morrissy logging handler
# Purpose:
#
# Author:      Robert Walker
#
# Created:     24/12/2014
#-------------------------------------------------------------------------------

import logging
import socket

class Morrissey_Handler(logging.Handler):

    def __init__(self, host = None, port = None):

        logging.Handler.__init__(self)
        self.morrissey = Morrissey(host, port)
        self.morrissey.report('EncodeSrv starting up')

    def emit(self, record):

        self.morrissey.report(record.getMessage())

class Morrissey(socket.socket):

    def __init__(self, host, port):

        port = int(port)
        try:
            socket.socket.__init__(self, socket.AF_INET, socket.SOCK_STREAM)
            self.connect((host, port))
            self.close()
        except:
            pass
        self.host = host
        self.port = port

    def report(self, thing, subdued = False):

        try:
            if not subdued:
                socket.socket.__init__(self, socket.AF_INET, socket.SOCK_STREAM)
                self.connect((self.host, self.port))
                self.sendall(thing + '\n')
            self.close()
        except:
            pass
