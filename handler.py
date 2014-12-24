#-------------------------------------------------------------------------------
# Name:        Morrissy logging handler
# Purpose:
#
# Author:      Robert Walker
#
# Created:     24/12/2014
#-------------------------------------------------------------------------------

import logging

class Morrissey_Handler(logging.Handler):

    def __init__(self, host = None, port = None):

        logging.Handler.__init__(self)
        self.host = host
        self.port = port

    def emit(self, record):
        socket.socket.__init__(self, socket.AF_INET, socket.SOCK_STREAM)
        self.connect((self.host, self.port))
        self.sendall(record + '\n')
        self.close()
