"""Tests for the data_array module."""

import os
import shutil
import unittest
from data_array import DataArray

TEST_DIR = '/tmp/data-array-tests'

def make_line(n):
    return ('%d ' % n) + '*' * int(('8%d' % n)[::-1])

class DataArrayTest(unittest.TestCase):
    def setUp(self):
        if os.path.exists(TEST_DIR):
            shutil.rmtree(TEST_DIR)

    def testDataArrayEmpty(self):
        array = DataArray(TEST_DIR, 4096)
        self.assertRaises(IndexError, lambda: array[0])

        count = 0
        for n, l in array.iteritems(0):
            count += 1
        self.assertEqual(count, 0)

        for n, l in array.iteritems(0, reverse=True):
            count += 1
        self.assertEqual(count, 0)

        self.assertEqual(array.begin(), 0)
        self.assertEqual(array.end(), 0)
        self.assertEqual(len(array), 0)

    def testDataArray(self):
        DataArray._block_size = 256
        array = DataArray(TEST_DIR, 4096, chunk_size=20)

        for i in xrange(100):
            array.append(make_line(i))

        self.assertEquals(array.begin(), 0)
        self.assertEquals(array.end(), 100)

        # Test indexing.
        for i in xrange(100):
            self.assertEquals(array[i], make_line(i))

        self.assertRaises(IndexError, lambda: array[-1])
        self.assertRaises(IndexError, lambda: array[100])

        # Test iteration.
        count = 0
        for n, l in array.iteritems():
            self.assertEquals(n, count)
            self.assertEquals(l, make_line(n))
            count += 1
            if count == 5:
                break
        for n, l in array.iteritems(5):
            self.assertEquals(n, count)
            self.assertEquals(l, make_line(n))
            count += 1
        self.assertEquals(count, 100)
        for n, l in array.iteritems(140):
            count += 1
        self.assertEquals(count, 100)

        # Test reverse iteration.
        count = 99
        for n, l in array.iteritems(reverse=True):
            self.assertEqual(n, count)
            self.assertEqual(l, make_line(n))
            count -= 1
            if count == 63:
                break
        for n, l in array.iteritems(63, reverse=True):
            self.assertEqual(n, count)
            self.assertEqual(l, make_line(n))
            count -= 1
        self.assertEqual(count, -1)
        for n, l in array.iteritems(-5, reverse=True):
            count -= 1
        self.assertEqual(count, -1)

        # Test persistence and starting with an empty cache.
        array = DataArray(TEST_DIR, 4096, chunk_size=20)
        self.assertEqual(len(array), 100)
        self.assertEqual(array[50], make_line(50))

        # Test truncate.
        self.assertEqual(array[0], make_line(0))
        array.truncate(60)
        self.assertTrue(0 < array.begin() <= 60)
        self.assertRaises(IndexError, lambda: array[0])

        # Test clear
        self.assertEqual(array.end(), 100)
        self.assertEqual(array[99], make_line(99))
        array.clear()
        self.assertEqual(len(array), 0)
        self.assertRaises(IndexError, lambda: array[99])

    def testNonzeroBase(self):
        DataArray._block_size = 256
        array = DataArray(TEST_DIR, 4096, chunk_size=20)

        array.append('14', seq=14)
        self.assertRaises(AssertionError, array.append, '15', 16)
        array.append('15', seq=15)

        self.assertEqual(array.begin(), 14)
        self.assertEqual(array.end(), 16)
        self.assertEqual(len(array), 2)
        self.assertEqual(array[15], '15')
        self.assertRaises(IndexError, lambda: array[16])

if __name__ == '__main__':
    unittest.main()
