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
        self.host = host
        self.port = port
        morrissey = socket.socket.__init__(self, socket.AF_INET, socket.SOCK_STREAM)
        morrissey.connect((self.host, self.port))
        morrissey.sendall('EncodeSrv starting up\n')
        morrissey.socket.close()

    def emit(self, record):
        morrissey = socket.socket.__init__(self, socket.AF_INET, socket.SOCK_STREAM)
        morrisseyconnect((self.host, self.port))
        morrissey.sendall(record + '\n')
        morrissey.socket.close()
