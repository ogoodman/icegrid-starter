import os
import shutil
import unittest
from file_dict import FileDict

TEST_DIR = '/tmp/file_dict_test'

class FileDictTest(unittest.TestCase):
    def setUp(self):
        if os.path.exists(TEST_DIR):
            shutil.rmtree(TEST_DIR)

    def test(self):
        d = FileDict(TEST_DIR)

        self.assertFalse('fred' in d)
        self.assertRaises(KeyError, lambda: d['fred'])

        del d['fred'] # no-op

        d['fred'] = 'Fred'

        self.assertTrue('fred' in d)
        self.assertEquals(d['fred'], 'Fred')

        d = FileDict(TEST_DIR)

        self.assertTrue('fred' in d)
        self.assertEquals(d['fred'], 'Fred')

        del d['fred']

        self.assertFalse('fred' in d)

        d = FileDict(TEST_DIR)

        self.assertFalse('fred' in d)
        self.assertRaises(KeyError, lambda: d['fred'])

if __name__ == '__main__':
    unittest.main()
