import sys
import unittest
from cStringIO import StringIO
from iceapp.printer import Printer

def grabOutput(func, *args):
    """Calls ``func(*args)`` capturing and returning stdout and stderr.

    :param func: a function to call
    :param args: arguments for *func*
    """
    ko, ke = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = StringIO(), StringIO()
    try:
        func(*args)
    except:
        traceback.print_exc()
    o, e = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = ko, ke
    return o.getvalue(), e.getvalue()

class PrinterTest(unittest.TestCase):
    def test(self):
        printer = Printer()

        self.assertEqual(printer.addOne(5), 6)

        output = grabOutput(printer.printString, 'Hello')
        self.assertEqual(output, ('Hello\n', ''))

        self.assertTrue(type(printer.getRand()) in (int, long))

if __name__ == '__main__':
    unittest.main()
