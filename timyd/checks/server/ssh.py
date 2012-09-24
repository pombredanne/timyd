import socket
import time

from timyd import Service, CheckFailure
from timyd.logged_properties import StringProperty

from .server import ServerService


class SSHService(ServerService):
    """A SSH server.
    """

    class ProtocolMismatch(CheckFailure):
        def __init__(self, msg):
            self.msg = unicode(msg)

        def __str__(self):
            return self.msg

    banner = StringProperty(
            "The banner sent by the server upon connection")

    def __init__(self, name, address, port=22):
        ServerService.__init__(self, name, address, port)

    def connected_check(self, s, addrinfo):
        banner = s.read_line(512)
        t = time.time() - self.check_start
        if banner is None or banner == '':
            raise SSHService.ProtocolMismatch("Unable to read SSH banner")
        self.banner = banner
        if t > 2:
            self.warning(
                    'ping',
                    "Reception of the banner took %f seconds" % (t,))
