from icecap.demo.printer import Printer
from icecap.base.event_source import EventSource

def setup(env):
    """Sets up the demo server by adding ``Printer`` servants to the
    ``Demo`` and ``DemoRep`` adapters.

    :param env: an environment resource factory
    """
    env.provide('printer', 'Demo', Printer(env))
    env.provide('printer', 'DemoRep', Printer(env))
    env.provide('events', 'Demo', EventSource(env, ''))
