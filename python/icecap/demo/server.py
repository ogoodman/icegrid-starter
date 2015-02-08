from icecap.base.antenna import Antenna
from icecap.demo.printer import Printer
from icecap.demo.event_source import EventSource

def init(env):
    """Sets up the demo server by adding servants to the
    ``Demo`` and ``DemoRep`` adapters.

    :param env: an environment resource factory
    """
    env.provide('printer', 'Demo', Printer(env))
    env.provide('printer', 'DemoRep', Printer(env))
    env.provide('events', 'Demo', EventSource(env, ''))
    env.provide('antenna', 'DemoRep', Antenna(env))
