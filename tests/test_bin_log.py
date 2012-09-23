import os
import struct
import time
import unittest

from timyd.logged_properties import BinaryLog, InvalidFile


class Test_read_bin_log(unittest.TestCase):
    FILE = 'tests/run_read.binlog'
    # 1 'name': 'remram'
    # 2 'age': 21
    # 3 'age': 22
    # 4 'name': 'remi'
    # 5 'age': 23
    # 5 summary (2 props)

    def setUp(self):
        if os.path.exists(self.FILE):
            os.remove(self.FILE)
        log = open(self.FILE, 'w')

        def i(nb):
            log.write(struct.pack('>q', nb))

        # header
        log.write('BINLOG01') # magic
        i(206) # offset of summary

        assert log.tell() == 16

        # property_change
        i(1) # time
        i(131) # next offset
        i(0) # previous offset
        log.write(struct.pack('>H', 4))
        log.write('name') # property_name
        log.write('s')
        log.write(struct.pack('>H', 6))
        log.write('remram') # value

        assert log.tell() == 55

        # property_change
        i(2) # time
        i(93) # next offset
        i(0) # previous offset
        log.write(struct.pack('>H', 3))
        log.write('age') # property_name
        log.write('i')
        i(21) # value

        assert log.tell() == 93

        # property_change
        i(3) # time
        i(168) # next offset
        i(55) # previous offset
        log.write(struct.pack('>H', 3))
        log.write('age') # property_name
        log.write('i')
        i(22) # value

        assert log.tell() == 131

        # property_change
        i(4) # time
        i(0) # next offset
        i(16) # previous offset
        log.write(struct.pack('>H', 4))
        log.write('name') # property_name
        log.write('s')
        log.write(struct.pack('>H', 4))
        log.write('remi') # value

        assert log.tell() == 168

        # property_change
        i(5) # time
        i(0) # next offset
        i(125) # previous offset
        log.write(struct.pack('>H', 3))
        log.write('age') # property_name
        log.write('i')
        i(23) # value

        assert log.tell() == 206
        
        # summary
        i(59) # length
        i(5) # time
        log.write(struct.pack('>H', 4))
        log.write('name') # property_name
        i(16) # first prop change offset
        i(131) # last prop change offset
        log.write(struct.pack('>H', 3))
        log.write('age') # property_name
        i(55) # first prop change offset
        i(168) # last prop change offset

        assert log.tell() == 265

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
