"""Publisher implements a simple event delivery mechanism.

A *publisher* has the following behaviour::

    pub = Publisher()
    pub.subcribe(channel, func, *args)
    pub.notify(channel, message) # results in func(message, *args)

.. note:: When func is a bound method, subscribe will only retain a weak
    reference to the object so that when the object becomes unreferenced it
    should be garbage collected and notifications to it will cease.
"""

import traceback
import types
import weakref

class SubscriberList(object):
    """A set of callables in which methods are held by weak reference."""

    def __init__(self):
        self._methods = weakref.WeakKeyDictionary()
        self._funcs = {}

    def add(self, func, *args):
        """Adds a callable.

        :param func: a function or bound method
        :param args: additional arguments to add when calling *func*
        """
        if type(func) is types.MethodType:
            self._methods[func.im_self] = (func.im_func.__name__, args)
        else:
            self._funcs[func] = args

    def remove(self, func):
        """Removes a callable.

        It is not an error to remove a callable which is not present.

        :param func: the callable to remove.
        """
        if type(func) is types.MethodType:
            self._methods.pop(func.im_self, None)
        else:
            self._funcs.pop(func, None)

    def iteritems(self):
        """Yields ``(func, args)`` for each added callable in the set."""
        for ob, info in self._methods.items():
            name, args = info
            yield getattr(ob, name), args
        for func, args in self._funcs.items():
            yield func, args

    def notify(self, info):
        """Calls each callable as ``func(info, args)``.
        
        Exceptions are printed to ``sys.stderr`` and not allowed to propagate.

        :param message: value to pass as first argument to each callable
        """
        for func, args in self.iteritems():
            try:
                func(info, *args)
            except:
                traceback.print_exc()

class Publisher(object):
    """A Publisher allows subscribers to listen for events on named channels.

    Usage::

        def func(info):
            # handle 'my-event' with the supplied info
    
        pub = Publisher()
        pub.subscribe('my-event', func)

        pub.notify('my-event', info) # passes info to func.

    Multiple subscribers can be added to each channel and all of them
    will be passed each event.
    """
    def __init__(self):
        self._channels = {}

    def notify(self, channel, info):
        """Send info to all subscribers to this channel.

        :param channel: the channel (or event name) on which to send
        :param info: information to pass to the subscribers
        """
        subs = self._channels.get(channel)
        if subs is not None:
            subs.notify(info)

    def subscribe(self, channel, func, *args):
        """Add a subscriber to the named channel.

        If func is an instance method it is held by weak reference
        so as not to interfere with normal garbage collection of its instance.

        :param channel: the channel (event name) to subscribe to
        :param func: callable to call for notifications on this channel
        :param args: optional arguments to add when notifying
        """
        if channel not in self._channels:
            self._channels[channel] = SubscriberList()
        self._channels[channel].add(func, *args)

    def unsubscribe(self, channel, func):
        """Remove a subscriber from the named channel.

        :param channel: the channel (event name) to unsubscribe from
        :param func: the callable to remove
        """
        if channel in self._channels:
            self._channels[channel].remove(func)
