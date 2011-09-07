import mailbox
import os.path
import os
import rfc822
import string
import socket
import time
import logging
import sys
import getopt


def mkMaildir(path):
    """Make a Maildir structure rooted at 'path'"""
    os.mkdir(path, 0700)
    os.mkdir(os.path.join(path, 'tmp'), 0700)
    os.mkdir(os.path.join(path, 'new'), 0700)
    os.mkdir(os.path.join(path, 'cur'), 0700)

def get_flname(obj):
    if sys.version_info[0] <= 2 and sys.version_info[1] < 5:
        return obj.name
    else:
        return obj._file.name

class MaildirWriter(object):

    """Deliver messages into a Maildir"""

    path = None
    counter = 0

    def __init__(self, path=None):
        """Create a MaildirWriter that manages the Maildir at 'path'

Arguments:
path -- if specified, used as the default Maildir for this object
"""
        if path != None:
            if not os.path.isdir(path):
                raise ValueError, 'Path does not exist: %s' % path
            self.path = path
        self.logger = logging.getLogger('MaildirWriter')

    def deliver(self, msg, path=None):
        """Deliver a message to a Maildir

Arguments:
msg -- a message object
path -- the path of the Maildir; if None, uses default from __init__
"""
        if path != None:
            self.path = path
        if self.path == None or not os.path.isdir(self.path):
            raise ValueError, 'Path does not exist'
        tryCount = 1
        srcFile = get_flname(msg.fp)
        (dstName, tmpFile, newFile, dstFile) = (None, None, None, None)
        while 1:
            try:
                dstName = "%d.%d_%d.%s" % (int(time.time()), os.getpid(),
                                           self.counter, socket.gethostname())
                tmpFile = os.path.join(os.path.join(self.path, "tmp"), dstName)
                newFile = os.path.join(os.path.join(self.path, "new"), dstName)
                self.logger.debug("deliver: attempt copy %s to %s" %
                              (srcFile, tmpFile))
                os.link(srcFile, tmpFile) # Copy into tmp
                self.logger.debug("deliver: attempt link to %s" % newFile)
                os.link(tmpFile, newFile) # Link into new
            except OSError, (n, s):
                self.logger.critical(
                        "deliver failed: %s (src=%s tmp=%s new=%s i=%d)" %
                        (s, srcFile, tmpFile, newFile, tryCount))
                self.logger.info("sleeping")
                time.sleep(2)
                tryCount += 1
                self.counter += 1
                if tryCount > 10:
                    raise OSError("too many failed delivery attempts")
            else:
                break

        # Successful delivery; increment deliver counter
        self.counter += 1

        # For the rest of this method we are acting as an MUA, not an MDA.

        # Move message to cur and restore any flags
        dstFile = os.path.join(os.path.join(self.path, "cur"), dstName)
        if msg.getFlags() != None:
            dstFile += ':' + msg.getFlags()
        self.logger.debug("deliver: attempt link to %s" % dstFile)
        os.link(newFile, dstFile)
        os.unlink(newFile)

        # Cleanup tmp file
        os.unlink(tmpFile)


class MessageDateError(TypeError):
    """Indicate that the message date was invalid"""
    pass


class MaildirMessage(rfc822.Message):
    
    """An email message

Has extra Maildir-specific attributes
"""

    def isFlagged(self):
        """return true if the message is flagged as important"""
        import re
        fname = get_flname(self.fp)
        if re.search(r':.*F', fname) != None:
            return True
        return False

    def getFlags(self):
        """return the flag part of the message's filename"""
        parts = get_flname(self.fp).split(':')
        if len(parts) == 2:
            return parts[1]
        return None

    def isNew(self):
        """return true if the message is marked as unread"""
        # XXX should really be called isUnread
        import re
        fname = get_flname(self.fp)
        if re.search(r':.*S', fname) != None:
            return False
        return True

    def getSubject(self):
        """get the message's subject as a unicode string"""

        import email.Header
        s = self.getheader("Subject")
        try:
            return u"".join(map(lambda x: x[0].decode(x[1] or 'ASCII', 'replace'),
                                email.Header.decode_header(s)))
        except(LookupError):
            return s

    def getSubjectHash(self):
        """get the message's subject in a "normalized" form

This currently means lowercasing and removing any reply or forward
indicators.
"""
        import re
        import string
        s = self.getSubject()
        if s == None:
            return '(no subject)'
        return re.sub(r'^(re|fwd?):\s*', '', string.strip(s.lower()))

    def getDateSent(self):
        """Get the time of sending from the Date header

Returns a time object using time.mktime. Not very reliable, because
the Date header can be missing or spoofed (and often is, by spammers).
Throws a MessageDateError if the Date header is missing or invalid.
"""
        dh = self.getheader('Date')
        if dh == None:
            return None
        try:
            return time.mktime(rfc822.parsedate(dh))
        except ValueError:
            raise MessageDateError("message has missing or bad Date")
        except TypeError: # gets thrown by mktime if parsedate returns None
            raise MessageDateError("message has missing or bad Date")
        except OverflowError:
            raise MessageDateError("message has missing or bad Date")

    def getDateRecd(self):
        """Get the time the message was received"""
        # XXX check that stat returns time in UTC, fix if not
        return os.stat(get_flname(self.fp))[8]

    def getDateSentOrRecd(self):
        """Get the time the message was sent, fall back on time received"""
        try:
            d = self.getDateSent()
            if d != None:
                return d
        except MessageDateError:
            pass
        return self.getDateRecd()

    def getAge(self):
        """Get the number of seconds since the message was received"""
        msgTime = self.getDateRecd()
        msgAge = time.mktime(time.gmtime()) - msgTime
        return msgAge / (60*60*24)



logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)
logger = logging.getLogger('zaa')

maildir = mailbox.Maildir('/tmp/Maildir/', MaildirMessage)
writer = MaildirWriter('/tmp/cur-output/')
for i, msg in enumerate(maildir):

    mdate = time.gmtime(msg.getDateSentOrRecd())
    datePart = str(mdate[0])
    subFolder = 'Archive.' + datePart
    sfPath = os.path.join('/tmp/cur-output',
                          '.' + subFolder)
    #logger.log(logging.INFO, "Archiving #%d to %s" %
    #         (i, subFolder), msg)
    
    # Create the subfolder if needed
    if not os.path.exists(sfPath):
        mkMaildir(sfPath)
    # Deliver
    writer.deliver(msg, sfPath)
    os.unlink(get_flname(msg.fp))
    
    #time.sleep(10000000)
