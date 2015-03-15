import os
import unittest
import simplejson as json
import shutil
from icecap.base.cap_dict import CapDict
from icecap.base.util import grabOutput
from data_relay import DataRelay

LISTING = '/tmp/data-relay-listing'

class FakeNode(object):
    def __init__(self):
        self._data = {}
        self._log = []
        self._relay = None
        self._pause_after = 10
        self._callbacks = []
        self._while_listing = []
        self._fail_update = False

    def list(self):
        for k in self._data.keys():
            yield k
            if self._while_listing:
                func, args = self._while_listing.pop(0)
                func(*args)

    def get(self, n):
        return self._log[n]

    def end(self):
        return len(self._log)

    def write(self, path, data):
        self._data[path] = data
        self._log.append(json.dumps(['w', path, data]))
        if self._relay is not None:
            self._relay.start()

    def remove(self, path):
        try:
            del self._data[path]
        except KeyError:
            return
        self._log.append(json.dumps(['r', path, None]))
        if self._relay is not None:
            self._relay.start()

    def dump(self, path):
        if path in self._data:
            d = [json.dumps(['w', path, self._data[path]]),]
        else:
            d = []
        return len(self._log), iter(d)

    def read(self, path):
        return self._data[path]

    def begin_update(self, update, on_ok, on_err):
        try:
            if self._fail_update:
                self._fail_update = False
                raise Exception('update failed')
            what, path, data = json.loads(update)
            if what == 'w':
                self.write(path, data)
            else:
                self.remove(path)
            if self._pause_after:
                on_ok()
                self._pause_after -= 1
            else:
                self._callbacks.append(on_ok)
        except Exception, e:
            on_err(e)

    def step(self, n):
        assert len(self._callbacks) == 1
        self._callbacks.pop()()
        self._pause_after = n - 1

    def setRelay(self, relay):
        self._relay = relay

    def doWhileListing(self, func, *args):
        self._while_listing.append((func, args))

    def logDir(self):
        if not os.path.exists(LISTING):
            os.makedirs(LISTING)
        return LISTING

class DataRelayTest(unittest.TestCase):
    def setUp(self):
        if os.path.exists(LISTING):
            shutil.rmtree(LISTING)

        # Set up two, as-yet unsynchronised nodes.
        self.source = FakeNode()
        self.target = FakeNode()

        self.source.write('a', 'Apple')
        self.source.write('b', 'Bear')
        self.source.write('c', 'Cat')

        # Set up a relay that will synchronise them.
        self.store = {}
        args = {'env': None, 'source': self.source, 'target': self.target}
        self.sinks = CapDict(self.store, args)
        self.sinks['relay'] = DataRelay(None, self.source, '', 'LISTING', target=self.target)
        self.relay = self.sinks['relay']

    def tearDown(self):
        self.relay = None
        self.sinks = None
        self.store = None
        self.target = None
        self.source = None

    def test(self):
        source, target, relay = self.source, self.target, self.relay

        source.setRelay(relay)
        relay.start()

        source.write('f', 'Fred')

        self.assertEqual(source._data, target._data)

        target._fail_update = True
        def do_write():
            source.write('f', 'Fish')
        out, err = grabOutput(do_write)
        self.assertTrue('update failed' in err)

        del self.sinks._cache['relay'] # Simulate loss of in-memory state.
        relay = self.sinks['relay']
        source.setRelay(relay)

        source.write('c', 'Chips')
        self.assertEqual(source._data, target._data)

    def testHaltDuringList(self):
        source, target, relay = self.source, self.target, self.relay

        source.setRelay(relay)
        def throw():
            raise Exception('bang')
        source.doWhileListing(throw)

        def do_start():
            relay.start()
        out, err = grabOutput(do_start)
        self.assertTrue('bang' in err)

        del self.sinks._cache['relay'] # Simulate loss of in-memory state.
        relay = self.sinks['relay']
        source.setRelay(relay)

        relay.start()
        relay.start()

        self.assertEqual(set(target.list()), set(['a', 'b', 'c']))
        self.assertEqual(target.read('c'), 'Cat')

    def testChangeDuringList(self):
        source, target, relay = self.source, self.target, self.relay

        source.doWhileListing(source.write, 'a', 'Antelope')
        source.doWhileListing(source.remove, 'b')

        source.setRelay(relay)
        relay.start()

        self.assertEqual(source._data, target._data)

    def testChangeDuringCopy(self):
        source, target, relay = self.source, self.target, self.relay

        target._pause_after = 1
        source.setRelay(relay)
        relay.start()

        self.assertEqual(relay._state, 'COPYING')
        source.write('b', 'Bean')
        source.write('d', 'Dog')
        source.remove('c')
        target.step(10)

        relay.run()
        self.assertEqual(source._data, target._data)

    def testStopDuringCopy(self):
        source, target, relay = self.source, self.target, self.relay

        target._pause_after = 1
        source.setRelay(relay)
        relay.start()

        self.assertEqual(relay._state, 'COPYING')

        target._callbacks = []
        target._pause_after = 10
        del self.sinks._cache['relay'] # Simulate loss of in-memory state.
        relay = self.sinks['relay']
        source.setRelay(relay)
        
        relay.start()

        self.assertEqual(source._data, target._data)

    def testUpdateEndsAfterList(self):
        source, target, relay = self.source, self.target, self.relay

        target._pause_after = 0
        source.setRelay(relay)
        source.doWhileListing(source.write, 'd', 'Dog')
        relay.start()

        self.assertEqual(relay._state, 'COPYING')
        target.step(10)
        relay.run()

        self.assertEqual(source._data, target._data)

if __name__ == '__main__':
    unittest.main()
