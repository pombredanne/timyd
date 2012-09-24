# At the time of writing, unicurses just doesn't work on Windows (pdcurses.dll
# lookup is wrong)
# This module provides escape sequences for terminal colors

import os


_DEFAULT = b'\x1B[0m'


class _ColorMethod(object):
    def __init__(self, code):
        self._code = code

    def __get__(self, obj, type=None):
        return self

    def __call__(self, msg):
        if colors._enabled:
            return "%s%s%s" % (self._code, msg, _DEFAULT)
        else:
            return msg


class _Colors(object):
    def __init__(self):
        self._enabled = None
        self.auto()

    def auto(self):
        if '/bin:' in os.getenv('PATH'):
            self.enable(True)
        else:
            self.enable(False)

    def enable(self, mode=True):
        self._enabled = mode

    black = _ColorMethod(b'\x1B[30m')
    red = _ColorMethod(b'\x1B[31m')
    green = _ColorMethod(b'\x1B[32m')
    yellow = _ColorMethod(b'\x1B[33m')
    blue = _ColorMethod(b'\x1B[34m')
    magenta = _ColorMethod(b'\x1B[35m')
    cyan = _ColorMethod(b'\x1B[36m')
    white = _ColorMethod(b'\x1B[37m')


colors = _Colors()
