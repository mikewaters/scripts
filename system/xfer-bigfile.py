#!/usr/bin/env python

"""
Incrementally transfer a big file over the network.

Written to backup a humongous .mbox file to a remote location
on a server that had 99% disk utilization.

Maps an open socket to a file-like-object, and writes to that
file using buffered reads.
Optionally truncates the source file after it has been transferred.

The destination server should be listening like:
    &> nc -l -p 6969 > destfile

mike waters 2011
"""

import shutil
import socket
import os.path

host = 'animal.suffolkcs.com'
port = 6969
sfile = '/var/mail/root'
truncate_after = True

try:

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))
    sockfile = sock.makefile('wb')

    with open(sfile) as f:
        shutil.copyfileobj(f, sockfile)
        sz = os.fstat(f.fileno())[6]

    sockfile.close()
    sock.close()

    if truncate_after:
        if os.path.getsize(sfile) == sz:
            f = open(sfile, 'w').close()

        else:
            print "file has been modified since we transferred it!"
            print "was ", sz

except Exception as e:
    print str(e)

