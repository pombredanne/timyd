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

        if self._dir == -1:
            next = prev

        if self._end is not None and ((self._dir == 1 and t > self._end) or
                (self._dir == -1 and t < self._end)):
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

    log = header, {property_change}, summary;
    header = "BINLOG01", integer (*summary offset*);
    summary = integer (*length*), time,
              {property_name,
               integer (*first prop change offset *),
               integer (*last prop change offset*)};
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
        # property name -> (first offset, last offset)
        self._property_updates = dict()

        self.debug = debug

        if readonly:
            self._file = open(filename, 'rb')
        else:
            try:
                self._file = open(filename, 'r+b')
            except IOError:
                # Python uses fopen(), which has a weird behavior with 'a+':
                # wherever the reading cursor is, writes would only happen at
                # the end of the file
                # Here we only use the mode 'r+b' which actually works,
                # creating the file before if necessary
                open(filename, 'wb').close()
            self._file = open(filename, 'r+b')
        self._file.seek(0, 2)
        self.readonly = readonly
        self._size = self._file.tell()

        if (not self.readonly) and self._size == 0:
            # Log just created, write header
            self._file.write('BINLOG01')
            self._size += 8
            self._write_integer(0)
            self._summary = None
        else:
            self._file.seek(0)
            if self._read(8) != 'BINLOG01':
                raise InvalidFile
            summary = self._read_integer()
            if summary < 16 or summary >= self._size:
                raise InvalidFile
            self._summary = summary
            self._file.seek(summary)
            t, props = self._read_summary()
            self._property_updates = props

    def _read_summary(self):
        if self.debug:
            sys.stderr.write("_read_summary @ %r\n" % self._file.tell())
        offset = self._file.tell()
        size = self._read_integer() # length
        if size < 32:
            raise InvalidFile
        t = self._read_integer() # time
        props = dict()
        end = offset + size
        offset = self._file.tell()
        while offset < end:
            prop = self._read_string()
            first = self._read_integer()
            last = self._read_integer()
            props[prop] = (first, last)
            offset = self._file.tell()
        return t, props

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
            sys.stderr.write("get_property(%r)\n" % prop)
        pos = self._property_updates[prop] # might raise KeyError
        self._file.seek(pos[1])
        t, next, prev, prop, value = self._read_property_change()
        return (t, value)

    def set_property(self, prop, value, t=None):
        """Records a new value of a property.
        """
        if self.readonly:
            raise ValueError("set_property() called on a readonly log")

        if not isinstance(value, (str, int, long)): # No unicode here
            raise TypeError

        if self.debug:
            sys.stderr.write("set_property(%r, %r)\n" % (prop, value))

        if t is None:
            t = int(time.time())

        if self._summary:
            if self.debug:
                sys.stderr.write("truncating summary\n")
            self._file.seek(self._summary)
            self._file.truncate()
            self._size = self._file.tell()
            self._summary = None

        try:
            pos = self._property_updates[prop] # might raise KeyError
            self._file.seek(pos[1] + 8)
            # Overwrite the next offset
            self._write_integer(self._size, overwrite=True)
        except KeyError:
            pos = None

        self._file.seek(0, 2)

        if pos is not None:
            self._property_updates[prop] = (pos[0], self._size)
        else:
            self._property_updates[prop] = (self._size, self._size)

        self._write_integer(t)
        self._write_integer(0)
        self._write_integer(pos[1] if pos else 0)
        self._write_string(prop)
        if isinstance(value, (int, long)):
            self._file.write('i')
            self._size += 1
            self._write_integer(value)
        else:
            self._file.write('s')
            self._size += 1
            self._write_string(value)

    def get_property_history(self, prop, start=None, end=None,
            dir=1, search=1):
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
        pos = self._property_updates[prop] # might raise KeyError
        if start is None:
            if dir == 1:
                return _PropertyIterator(self, pos[0], end, dir=1)
            else:
                return _PropertyIterator(self, pos[1], end, dir=-1)

        if search == 1:
            pos = pos[0]
            def found(tm):
                return tm >= start
            def nextpos(prev, next):
                return next
            t = start - 1
        elif search == -1:
            pos = pos[1]
            def found(tm):
                return tm <= start
            def nextpos(prev, next):
                return prev
            t = start + 1

        last = pos
        while pos != 0:
            self._file.seek(pos)
            t, next, prev, prop, value = self._read_property_change()
            if found(t):
                if search != dir and t != start:
                    return _PropertyIterator(self, last, end, dir=dir)
                else:
                    return _PropertyIterator(self, pos, end, dir=dir)
            last = pos
            pos = nextpos(prev, next)
        return _PropertyIterator(None, None) # empty iterator

    def close(self, t=None):
        if not self.readonly and self._summary is None:
            self.write_summary(t)
        self._file.close()
        if self.debug:
            sys.stderr.write("closed\n\n")

    def write_summary(self, t=None):
        if t is None:
            t = int(time.time())

        if self._summary is not None:
            raise ValueError("write_summary() called on already summarized "
                             "binary log")

        offset = self._size

        self._file.seek(8)
        self._write_integer(
                offset,
                overwrite=True)
        self._file.seek(0, 2)

        self._write_integer(0) # length: overwrite later - probably inefficient
        self._write_integer(t) # time
        for prop, offsets in self._property_updates.iteritems():
            self._write_string(prop)
            self._write_integer(offsets[0])
            self._write_integer(offsets[1])

        size = self._file.tell() - offset
        self._file.seek(offset)
        self._write_integer(size, overwrite=True)

        self._summary = offset

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
