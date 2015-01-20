"""Tests for the data_log module."""

import os
import shutil
import unittest
from data_log import DataLog, neb_escape, neb_unescape

TEST_DIR = '/tmp/data-log-tests'

def make_line(n):
    return ('%d ' % n) + '*' * int(('8%d' % n)[::-1])

class DataLogTest(unittest.TestCase):
    def setUp(self):
        if os.path.exists(TEST_DIR):
            shutil.rmtree(TEST_DIR)

    def testDataLogEmpty(self):
        log = DataLog(TEST_DIR, 4096)
        self.assertRaises(IndexError, log.__getitem__, 0)

        count = 0
        for n, l in log.iteritems(0):
            count += 1
        self.assertEqual(count, 0)

        for n, l in log.iteritems(0, reverse=True):
            count += 1
        self.assertEqual(count, 0)

        self.assertEqual(log.first(), None)
        self.assertEqual(log.last(), None)

        # Simulate write in progress, nothing written yet.
        with open(os.path.join(TEST_DIR, 'data.0'), 'w') as out:
            out.write('')

        self.assertRaises(IndexError, log.__getitem__, 0)

        # Simulate write in progress, no complete line written yet.
        with open(os.path.join(TEST_DIR, 'data.0'), 'w') as out:
            out.write('10')

        self.assertEqual(log.first(), None)
        self.assertEqual(log.last(), None)

        self.assertRaises(IndexError, log.__getitem__, 0)

    def testDataLog(self):
        DataLog._block_size = 256
        log = DataLog(TEST_DIR, 4096)

        for i in xrange(100):
            log.append(make_line(i))

        self.assertEquals(log.first(), 0)
        self.assertEquals(log.last(), 99)

        # Simulate a partial write to end of log.
        fh = open(os.path.join(TEST_DIR, 'data.%d' % log._nums()[-1]), 'a')
        fh.write('10')
        fh.close()

        # Test indexing.
        for i in xrange(100):
            self.assertEquals(log[i], make_line(i))

        self.assertRaises(IndexError, log.__getitem__, -1)
        self.assertRaises(IndexError, log.__getitem__, 100)

        # Test iteration.
        count = 0
        for n, l in log.iteritems():
            self.assertEquals(n, count)
            self.assertEquals(l, make_line(n))
            count += 1
            if count == 5:
                break
        for n, l in log.iteritems(5):
            self.assertEquals(n, count)
            self.assertEquals(l, make_line(n))
            count += 1
        self.assertEquals(count, 100)
        for n, l in log.iteritems(140):
            count += 1
        self.assertEquals(count, 100)

        # Test reverse iteration.
        count = 99
        for n, l in log.iteritems(reverse=True):
            self.assertEqual(n, count)
            self.assertEqual(l, make_line(n))
            count -= 1
            if count == 63:
                break
        for n, l in log.iteritems(63, reverse=True):
            self.assertEqual(n, count)
            self.assertEqual(l, make_line(n))
            count -= 1
        self.assertEqual(count, -1)
        for n, l in log.iteritems(-5, reverse=True):
            count -= 1
        self.assertEqual(count, -1)

        # Test corner-cases in _seek_start_of_line.
        fh = log._open(5)
        count = 1
        while log._seek_next_line(fh):
            count += 1
        fh.seek(3200)
        log._seek_start_of_line(fh)
        fh.seek(500)
        log._seek_start_of_line(fh)
        self.assertEquals(fh.tell(), 0)

        # Test deleting a chunk. (Not expected, but wanted for robustness.)
        os.unlink(os.path.join(TEST_DIR, 'data.%d' % 4))
        #for n in log._nums():
        #    print n, log._seq_start(n)

        self.assertRaises(IndexError, log.__getitem__, 54)

        # Test truncate.
        log.truncate(60)
        self.assertTrue(0 < log.first() <= 60)

    def testDataLogGaps(self):
        DataLog._block_size = 256
        log = DataLog(TEST_DIR, 4096)

        log.append('hello', -5)
        log.append('there')
        for i in xrange(10):
            log.append(make_line(3*i), 3*i)

        self.assertEquals(log[-5], 'hello')
        self.assertRaises(IndexError, log.__getitem__, -3)
        self.assertRaises(IndexError, log.__getitem__, 1)

        count = 0
        for n, l in log.iteritems(1):
            self.assertEquals(l, make_line(n))
            count += 1
        self.assertEquals(count, 9)

        seq_list = []
        for n, l in log.iteritems(reverse=True):
            seq_list.append(n)
        self.assertEquals(seq_list, [27, 24, 21, 18, 15, 12, 9, 6, 3, 0, -4, -5])

        for n, l in log.iteritems(15, reverse=True):
            break
        self.assertEqual(n, 15)

    def test_neb_escape(self):
        orig = '\\1\\\\2\\\\\\3\n\\\n\\\\\n'
        esc = neb_escape(orig)
        self.assertEquals(orig, neb_unescape(esc))

if __name__ == '__main__':
    unittest.main()
