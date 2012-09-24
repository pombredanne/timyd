import socket
import time

from timyd import Service, CheckFailure
from timyd.logged_properties import StringProperty

from .server import ServerService


class SMTPService(ServerService):
    """A SMTP server.
    """

    class ProtocolMismatch(CheckFailure):
        def __init__(self, msg):
            self.msg = unicode(msg)

        def __str__(self):
            return self.msg

    banner = StringProperty('banner')

    def __init__(self, name, address, port=25, rcpt=True,
            from_host='smtp_test.monitor.org'):
        ServerService.__init__(self, name, address, port)
        self.rcpt = rcpt
        self.from_host = from_host

    def connected_check(self, s, addrinfo):
        banner = s.read_line(512)
        t = time.time() - self.check_start
        if banner is None or banner == '':
            raise SMTPService.ProtocolMismatch("Unable to read SMTP banner")
        if not banner.startswith("220 "):
            raise SMTPService.ProtocolMismatch(
                    "Server did not send 220 banner")
        self.banner = banner
        if t > 2:
            self.warning(
                    'ping',
                    "Reception of the banner took %f seconds" % (t,))
        if self.rcpt:
            s.send("EHLO %s\r\n" % self.from_host)
            # TODO : attempt to send a message, check it is accepted
            # (stop before DATA)
        s.send("QUIT\r\n")
