#!/usr/bin/python
"""Script to start encodesrv as a daemon. Uses encodesrv.daemon module to
do all the fancy stuff with redirects.
"""


import encodesrv
from encodesrv import daemon
import sys


class EncodeSrvDaemon(encodesrv.EncodeSrv, daemon.Daemon):
    
    def __init__(self, *args, **kwargs):
        
        daemon.Daemon.__init__(self, *args, **kwargs)

if __name__ == "__main__":
    daemon = EncodeSrvDaemon('/tmp/encodesrv.pid')
    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            daemon.start()
        elif 'stop' == sys.argv[1]:
            daemon.stop()
        elif 'restart' == sys.argv[1]:
            daemon.restart()
        else:
            print("Unknown command")
            sys.exit(2)
        sys.exit(0)
    else:
        print("usage: {} start|stop|restart".format(sys.argv[0]))
        sys.exit(2)
