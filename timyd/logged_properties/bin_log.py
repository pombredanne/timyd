import struct
import sys
import time


class InvalidFile(Exception):
    """Formatting error in a BinaryLog.
    """


class _PropertyIterator(object):
    def __init__(self, log, next_pos, end=None, dir=1):
        self._log = log
        self._next_pos = next_pos
        self._end = end
        self._dir = dir

    def next(self):
        if self._next_pos is None:
            raise StopIteration
        self._log._file.seek(self._next_pos)
        t, next, prev, prop, value = self._log._read_property_change()
        r = False

        if dir == -1:
            next = prev

        if (dir == 1 and t > end) or (dir == -1 and t < end):
            next = 0
            r = True

        if next != 0:
            self._next_pos = next
        else:
            self._next_pos = None
            self._log = None # lose that reference

        if r:
            raise StopIteration

        return (t, value)

    def __iter__(self):
        return self


class BinaryLog(object):
    """A binary log.

    log = header, {summary, {property_change}};
    header = "BINLOG01", integer (*last summary offset*);
    summary = integer (*length*), time,
              integer (*next offset*), integer (*previous offset*),
              {property_name, integer (*last prop change offset*)};
    property_change = time,
                      integer (*next offset*), integer (*previous offset*),
                      property_name, value;
    property_name = string;
    value = ('s', string) | ('i', integer);
    time = integer;

    Strings are prefixed with a 16-bit length in big endian.
    Integers are 64-bit, signed, big endian.
    Times are represented as UNIX timestamps.
    """

    def __init__(self, filename, readonly=False, debug=False):
        # property name -> offset
        self._last_property_update = dict()

        self.debug = debug

        if readonly:
            self._file = open(filename, 'rb')
        else:
            try:
                self._file = open(filename, 'r+b')
            except IOError:
                # mode 'a+b' doesn't work; we create it but still open with r+b
                open(filename, 'w').close()
            self._file = open(filename, 'r+b')
        self._file.seek(0, 2)
        self.readonly = readonly
        self._size = self._file.tell()

        if (not self.readonly) and self._size == 0:
            # Log just created, write header
            self._file.write('BINLOG01')
            self._size += 8
            self._write_integer(0)
            # Write an empty summary
            self._last_summary_offset = None
            self.write_summary()
        else:
            self._file.seek(0)
            if self._read(8) != 'BINLOG01':
                raise InvalidFile
            last_summary = self._read_integer()
            if last_summary < 16 or last_summary > self._size:
                raise InvalidFile
            self._last_summary_offset = last_summary
            self._file.seek(last_summary)
            t, next, prev, props = self._read_summary()
            self._last_property_update.update(props)
            self._ends_with_summary = self._file.tell() == self._size
            if not self._ends_with_summary:
                offset = self._file.tell()
                while offset != self._size:
                    t, next, prev, prop, value = self._read_property_change()
                    self._last_property_update[prop] = offset

                    offset = self._file.tell()

    def _read_summary(self):
        if self.debug:
            sys.stderr.write("_read_summary @ %r\n" % self._file.tell())
        offset = self._file.tell()
        size = self._read_integer() # length
        if size < 32:
            raise InvalidFile
        t = self._read_integer() # time
        next = self._read_integer() # next offset
        prev = self._read_integer() # previous offset
        props = dict()
        end = offset + size
        offset = self._file.tell()
        while offset < end:
            prop = self._read_string()
            o = self._read_integer()
            props[prop] = o
            offset = self._file.tell()
        return t, next, prev, props

    def _read_property_change(self):
        if self.debug:
            sys.stderr.write("_read_property_change @ %r\n" %
                             self._file.tell())
        return (self._read_integer(), # time
                self._read_integer(), # next offset
                self._read_integer(), # previous offset
                self._read_string(), # property_name
                self._read_value()) # value

    def get_property(self, prop):
        """Gets the current value of a property.
        """
        if self.debug:
            sys.stderr.write("get_property(%r)" % prop)
        pos = self._last_property_update[prop] # might raise KeyError
        self._file.seek(pos)
        t, next, prev, prop, value = self._read_property_change()
        return (t, value)

    def set_property(self, prop, value, t=None):
        """Records a new value of a property.
        """
        if not isinstance(value, (str, int, long)): # No unicode here
            raise TypeError
        
        if self.debug:
            sys.stderr.write("set_property(%r, %r)\n" % (prop, value))

        if t is None:
            t = int(time.time())

        try:
            last_pos = self._last_property_update[prop]
            self._file.seek(last_pos + 8)
            # Overwrite the next offset
            self._write_integer(self._size, overwrite=True)
        except KeyError:
            last_pos = 0

        self._file.seek(0, 2)

        self._last_property_update[prop] = self._size

        self._write_integer(t)
        self._write_integer(0)
        self._write_integer(last_pos)
        self._write_string(prop)
        if isinstance(value, (int, long)):
            self._file.write('i')
            self._size += 1
            self._write_integer(value)
        else:
            self._file.write('s')
            self._size += 1
            self._write_string(value)

        self._ends_with_summary = False

    def get_property_history(self, prop, start=None, end=None,
            dir=1, search=-1):
        """Gets the previous values of a property.

        start is the time we want to iterate from.
        Iteration will stop if end is reached.
        dir is either 1 (iterate in the order of the records in the file) or -1
        (iterate in reverse order). If dir is -1, start will probably be the
        more recent record returned, and end should probably be smaller.
        search indicates how to look for start in the file; either reading from
        the beginning (1, default) or the end (-1). Use it if you know the
        requested position is closer to one extremity of the file.
        """
        # TODO : find start
        return _PropertyIterator(self, next_pos, end)

    def close(self, t=None):
        if not self.readonly and not self._ends_with_summary:
            self.write_summary(t)
        self._file.close()
        if self.debug:
            sys.stderr.write("closed\n\n")

    def write_summary(self, t=None):
        if t is None:
            t = int(time.time())

        offset = self._size

        self._file.seek(8)
        self._write_integer(
                offset,
                overwrite=True)
        self._file.seek(0, 2)

        self._write_integer(0) # length: overwrite later - probably inefficient
        self._write_integer(t) # time
        self._write_integer(0) # next offset
        # previous offset
        if self._last_summary_offset is None:
            self._write_integer(0)
        else:
            self._write_integer(self._last_summary_offset)
        for prop, p_offset in self._last_property_update.iteritems():
            self._write_string(prop)
            self._write_integer(p_offset)

        size = self._file.tell() - offset
        self._file.seek(offset)
        self._write_integer(size, overwrite=True)


        self._last_summary_offset = offset
        self._ends_with_summary = True

    def _read(self, size):
        s = self._file.read(size)
        if len(s) != size:
            raise InvalidFile
        return s

    def _read_value(self):
        if self.debug:
            sys.stderr.write("_read_value @ %r\n" % self._file.tell())
        t = self._file.read(1)
        if t == b'i':
            return self._read_integer()
        elif t == b's':
            return self._read_string()
        else:
            raise InvalidFile

    def _read_string(self):
        if self.debug:
            sys.stderr.write("_read_string @ %r" % self._file.tell())
        by = self._file.read(2)
        if len(by) != 2:
            raise InvalidFile
        l = struct.unpack('>H', by)[0]
        s = self._file.read(l)
        if len(s) != l:
            raise InvalidFile
        if self.debug:
            sys.stderr.write(" = %r\n" % s)
        return s

    def _write_string(self, s):
        self._file.write(struct.pack('>H', len(s)))
        self._file.write(s)
        self._size += 2 + len(s)

    def _read_integer(self):
        if self.debug:
            sys.stderr.write("_read_integer @ %r" % self._file.tell())
        by = self._file.read(8)
        if len(by) != 8:
            raise InvalidFile
        if self.debug:
            sys.stderr.write(" = %r\n" % struct.unpack('>q', by)[0])
        return struct.unpack('>q', by)[0]

    def _write_integer(self, nb, overwrite=False):
        self._file.write(struct.pack('>q', nb))
        if not overwrite:
            self._size += 8

    def __getitem__(self, prop):
        t, value = self.get_property(prop)
        return value

    def __setitem__(self, prop, value):
        self.set_property(prop, value)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()
        return False
