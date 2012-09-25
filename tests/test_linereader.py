import socket
import time
import unittest


from timyd.checks.server.server import LineReader, InvalidLine, TimedOut


class FakeSocket(object):
    def __init__(self, timeout, responses):
        self.timeout = timeout
        self.responses = responses

    def gettimeout(self):
        return self.timeout

    def recv(self, max):
        try:
            r = self.responses.pop(0)
            if not isinstance(r, str):
                return r(max)
            if len(r) > max:
                self.responses.insert(0, r[max:])
                return r[:max]
            return r
        except IndexError:
            raise socket.error


class Test_linereader(unittest.TestCase):
    def test_simple(self):
        s = FakeSocket(2, ["rem", "ram\nwrote ", "this\r\n", "in ", "Python"])
        r = LineReader(s)

        self.assertEqual(r.read_line(100), "remram")
        self.assertEqual(r.read_line(100), "wrote this")
        self.assertRaises(socket.error, r.read_line, 100)

    def test_dos(self):
        s = FakeSocket(2, ["remi ", "\"remram\" ", "rampin\n"])
        r = LineReader(s)

        self.assertRaises(InvalidLine, r.read_line, 16)

    def test_timeout(self):
        def out(max):
            time.sleep(3)
            return "r"
        s = FakeSocket(2, ["remi ", out, "ampin\nfoo"])
        r = LineReader(s)

        self.assertRaises(TimedOut, r.read_line, 100)
