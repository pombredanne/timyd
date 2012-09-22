import os
import struct
import time
import unittest

from timyd.logged_properties import BinaryLog, InvalidFile


class Test_read_bin_log(unittest.TestCase):
    FILE = 'tests/run_read.binlog'
    # 0 summary (empty)
    # 1 'name': 'remram'
    # 2 'age': 21
    # 3 'age': 22
    # 3 summary (2 props)
    # 4 'name': 'remi'
    # 5 'age': 23

    def setUp(self):
        if os.path.exists(self.FILE):
            os.remove(self.FILE)
        log = open(self.FILE, 'w')

        def i(nb):
            log.write(struct.pack('>q', nb))

        # header
        log.write('BINLOG01') # magic
        i(163) # offset of last summary

        assert log.tell() == 16

        # summary
        i(32) # length
        i(0) # time
        i(163) # next offset
        i(0) # previous offset

        assert log.tell() == 48

        # property_change
        i(1) # time
        i(222) # next offset
        i(0) # previous offset
        log.write(struct.pack('>H', 4))
        log.write('name') # property_name
        log.write('s')
        log.write(struct.pack('>H', 6))
        log.write('remram') # value

        assert log.tell() == 87

        # property_change
        i(2) # time
        i(125) # next offset
        i(0) # previous offset
        log.write(struct.pack('>H', 3))
        log.write('age') # property_name
        log.write('i')
        i(21) # value

        assert log.tell() == 125

        # property_change
        i(3) # time
        i(259) # next offset
        i(87) # previous offset
        log.write(struct.pack('>H', 3))
        log.write('age') # property_name
        log.write('i')
        i(22) # value

        assert log.tell() == 163

        # summary
        i(59) # length
        i(3) # time
        i(0) # next offset
        i(16) # previous offset
        log.write(struct.pack('>H', 4))
        log.write('name') # property_name
        i(48) # last prop change offset
        log.write(struct.pack('>H', 3))
        log.write('age') # property_name
        i(125) # last prop change offset

        assert log.tell() == 222

        # property_change
        i(4) # time
        i(0) # next offset
        i(48) # previous offset
        log.write(struct.pack('>H', 4))
        log.write('name') # property_name
        log.write('s')
        log.write(struct.pack('>H', 4))
        log.write('remi') # value

        assert log.tell() == 259

        # property_change
        i(5) # time
        i(0) # next offset
        i(125) # previous offset
        log.write(struct.pack('>H', 3))
        log.write('age') # property_name
        log.write('i')
        i(23) # value

        assert log.tell() == 297

        log.close()

    def tearDown(self):
        os.remove(self.FILE)

    def test_read_props(self):
        """Reads the last value of properties.
        """
        with BinaryLog(self.FILE, readonly=True, debug=True) as log:
            self.assertEqual(log.get_property('name'), (4, 'remi'))
            self.assertEqual(log.get_property('age'), (5, 23))

            self.assertEqual(log['name'], 'remi')
            self.assertEqual(log['age'], 23)

#    def test_iter_props(self):
#        """Reads the history of properties.
#        """
#        with BinaryLog(self.FILE, readonly=True) as log:
#            ages = log.get_property_history('age', 3)
#            self.assertEqual(ages.next(), (3, 22))
#            self.assertEqual(ages.next(), (5, 23))
#            self.assertRaises(StopIteration, ages.next)
#
#            names = log.get_property_history('name', None, 5)
#            self.assertEqual(names.next(), (1, 'remram'))
#            self.assertEqual(names.next(), (4, 'remi'))
#            self.assertRaises(StopIteration, names.next)


class Test_write_bin_log(unittest.TestCase):
    FILE = 'tests/run_write.binlog'

    def setUp(self):
        if os.path.exists(self.FILE):
            os.remove(self.FILE)

    def test_simple(self):
        """Writes some properties and read them back.
        """
        with BinaryLog(self.FILE, debug=True) as log:
            log.set_property('name', "remi")
            self.assertRaises(KeyError, log.get_property, 'age')
            log.set_property('age', 20)
            self.assertEqual(log.get_property('name')[1], "remi")
        with BinaryLog(self.FILE, debug=True) as log:
            log.set_property('age', 21)
            self.assertEqual(log.get_property('name')[1], "remi")
            self.assertEqual(log.get_property('age')[1], 21)
