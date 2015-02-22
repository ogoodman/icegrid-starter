import os
import unittest
from cap_dict import CapDict
from icecap.demo.person import Person

class CapTest(unittest.TestCase):
    def test(self):
        d = CapDict({})

        d['oliver'] = Person('Oliver', '18/07/1965')
        self.assertFalse('oliver' in d._cache)

        o = d['oliver']
        self.assertEqual(str(o), 'name: Oliver, dob: 18/07/1965')

        o._name = 'Ollie'
        o._save(o)
        del o
        self.assertFalse('oliver' in d._cache)

        o = d['oliver']
        self.assertEqual(o._name, 'Ollie')

        self.assertRaises(KeyError, lambda: d['fred'])

        del d['fred'] # no-op

        del d['oliver']
        self.assertRaises(KeyError, lambda: d['oliver'])

        extra = {'env': 'ENV'}
        d = CapDict({}, extra=extra)
        d['fred'] = Person('Fred', '2/6/1967')

        self.assertEqual(d['fred']._env, 'ENV')

        self.assertFalse('fred' in d._cache)

        extra['env'] = 'NEWENV'
        self.assertEqual(d['fred']._env, 'NEWENV')

if __name__ == '__main__':
    unittest.main()
