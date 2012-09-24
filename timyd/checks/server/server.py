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


class InvalidLine(CheckFailure):
    def __str__(self):
        return "Line too long - wrong protocol or DoS attempt?"


class LineReader(object):
    """Wrapper for a socket allowing to read one line at a time.
    """

    def __init__(self, sock):
        self._sock = sock
        self._buf = ''

    def settimeout(self, tm):
        self._sock.settimeout(tm)

    def read_line(self, max):
        start = time.time()
        tm = self._sock.gettimeout()
        p = self._buf.find('\n')
        if p >= 0:
            l = self._buf[:p]
            if l[-1] == '\r':
                l = l[:-1]
            return l
        while len(self._buf) < max:
            data = self._sock.recv(max - len(self._buf))
            p = data.find('\n')
            if p >= 0:
                l = self._buf + data[:p]
                self._buf = data[p+1:]
                if l[-1] == '\r':
                    l = l[:-1]
                return l
            self._buf += data
            now = time.time()
            if tm and now - start > tm:
                raise TimedOut(u"Timed out while reading a line after %fs" %
                        (now - start))
        raise InvalidLine

    def send(self, data):
        self._sock.send(data)

    def close(self):
        self._sock.close()


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
            reader = LineReader(s)
            try:
                self.connected_check(reader, info)
            finally:
                reader.close()
            return
        raise CantConnect(self.address, self.port)

    def connected_check(self, s, addrinfo):
        """Default version of connected_check() does nothing.

        If we could establish a connection, the test passes. Override this
        method to provide protocol-specific tests.
        """
