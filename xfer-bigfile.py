#!/usr/bin/env python

"""
Incrementally transfer a big file over the network.

"""

import shutil
import socket
import os.path

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(('localhost', 6969))
sockfile = sock.makefile('wb')

sfile = 'test.log'

with open(sfile) as f:
    shutil.copyfileobj(f, sockfile)
    sz = os.fstat(f.fileno())[6]

sockfile.close()
sock.close()

if os.path.getsize(sfile) == sz:
    f = open(sfile, 'w').close()

else:
    print "file has been modified since we transferred it!"
    print "was ", sz
