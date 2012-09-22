import socket
import time

from timyd import Service, CheckFailure


class CantResolve(CheckFailure):
    def __init__(self, address):
        self.address = address

    def __str__(self):
        return u"Can't resolve %s" % (self.address,)

class CantConnect(CheckFailure):
    def __init__(self, address, port):
        self.address = address
        self.port = port

    def __str__(self):
        return u"Can't connect to %s:%d" % (self.address, self.port)


class TimedOut(CheckFailure):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg


def _read_line(s, max):
    t = time.time()
    tm = s.gettimeout()
    buf = ''
    while len(buf) < max:
        data = s.recv(max - len(buf))
        p = data.find('\n')
        if p >= 0:
            buf += data[:p]
            if buf[-1] == '\r':
                buf = buf[:-1]
            return buf
        buf += data
        now = time.time()
        if tm and now - t > tm:
            raise TimedOut(u"Timed out while reading a line after %fs" % now)
    return None


class ServerService(Service):
    """A generic server.

    Subclasses provide specific behavior for different kind of services checks
    that connect to a server.
    """

    def __init__(self, name, address, port):
        Service.__init__(self, name)
        self.address = address
        self.port = port

    def check(self):
        try:
            addresses = socket.getaddrinfo(
                    self.address, self.port,
                    socket.AF_UNSPEC, socket.SOCK_STREAM)
        except socket.gaierror:
            raise CantResolve(self.address)
        if not addresses:
            raise CantResolve(self.address)
        elif len(addresses) > 1:
            self.warning("Multiple addresses available for %s:%d" % (
                    self.address, self.port))

        for info in addresses:
            af, socktype, proto, canonname, sa = info
            try:
                s = socket.socket(af, socktype, proto)
            except socket.error, e:
                continue
            s.settimeout(10)
            try:
                self.check_start = time.time()
                s.connect(sa)
            except socket.error, e:
                s.close()
                continue
            try:
                self.connected_check(s, info)
            finally:
                s.close()
            return
        raise SSHService.CantConnect(self.address, self.port)

    def connected_check(self, s, addrinfo):
        """Default version of connected_check() does nothing.

        If we could establish a connection, the test passes. Override this
        method to provide protocol-specific tests.
        """
