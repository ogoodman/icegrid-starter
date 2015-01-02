import os
import unittest
from icecap.base import util

class UtilTest(unittest.TestCase):
    def test(self):
        self.assertTrue('slice' in os.listdir(util.appRoot()))

        app_root_fn = util.importSymbol('icecap.base.util.appRoot')
        self.assertEqual(app_root_fn, util.appRoot)

        # grabOutput captures stdout and stderr for the duration of a call.
        def echo(msg):
            print msg
        so, se = util.grabOutput(echo, 'Hi')
        self.assertEqual((so, se), ('Hi\n', ''))

        # Exceptions are trapped and traceback reported from stderr.
        so, se = util.grabOutput('not a func', 'arg')
        self.assertEqual(so, '')
        self.assertTrue('TypeError' in se)

if __name__ == '__main__':
    unittest.main()