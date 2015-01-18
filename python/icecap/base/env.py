"""The *environment* interface abstracts the environment for all grid participants.

An ``Env`` instance is generally created once at the top-level of any
client or server code. It provides a single point where all environmental
dependencies can be injected.

A ``FakeEnv`` implementing versions of all the same public methods
can be used for testing.

The ``Env`` abstraction reduces server implementation to nothing more than
a function taking an *env* object.

Server example::

    # This can be run by servers/gen_server.py, or called in test setup.
    def server(env):
        env.provide('name', 'Adapter', Servant(env))

Client example::

    env = Env() # or FakeEnv()

    proxy = env.getProxy('name@Adapter-node1.Adapter')
    proxy.doSomething()

"""

import atexit
import sys
import Ice
import icegrid_config
from icecap.base.util import importSymbol

def toMostDerived(ob):
    """Converts any ice proxy to its most derived type.

    Queries the proxy for its type, imports the appropriate specific
    class, and casts to that type.

    Returns any non-proxy unchanged.

    :param ob: an Ice.ObjectPrx (in the interesting case anyway).
    """
    if type(ob) is not Ice.ObjectPrx:
        return ob
    cls_name = ob.ice_id().replace('::', '.')[1:] + 'Prx'
    cls = importSymbol(cls_name)
    return cls.uncheckedCast(ob)

class Env(object):
    """The core environment resource factory. Mediates access to all environment 
    resources such as files, Ice connections, HTTP requests, etc.

    .. note:: The current version only implements IceGrid connection methods.
    """
    def __init__(self):
        self._ic = None
        self._adapters = {}
        self._query = None

    def _communicator(self):
        """Returns the Ice.Communicator for the configured grid."""
        if self._ic is None:
            self._ic = Ice.initialize(sys.argv)
            atexit.register(self._ic.destroy)

            reg_proxy = self._ic.stringToProxy("IceGrid/Locator:tcp -h %s -p 4061" % icegrid_config.ICE_REG_HOST)
            registry = Ice.LocatorPrx.uncheckedCast(reg_proxy)
            self._ic.setDefaultLocator(registry)
        return self._ic

    def dataDir(self):
        """Returns the local data directory path."""
        return icegrid_config.DATA_ROOT

    def getProxy(self, addr):
        """Gets a proxy for the servant (if any) at the specified address.

        The servant is queried for its type and cast to the appropriate
        proxy type.

        :param addr: proxy string for the required proxy
        """
        ic = self._communicator()
        return toMostDerived(ic.stringToProxy(addr))

    def provide(self, name, adapter, servant):
        """Adds a servant at the specified name and adapter id.

        :param name: the name at which to provide the servant
        :param adapter: the id of the adapter to which to add the servant
        :param servant: the servant to be provided
        """
        ic = self._communicator()
        if adapter not in self._adapters:
            self._adapters[adapter] = ic.createObjectAdapter(adapter)
        proxy = self._adapters[adapter].add(servant, ic.stringToIdentity(name))
        s_cls = servant.ice_staticId().replace('::', '.')[1:]
        proxy_cls = importSymbol(s_cls + 'Prx')
        servant._proxy = proxy_cls.uncheckedCast(proxy)

    def replicas(self, proxy):
        """Returns a list containing all registered replicas of the proxy.

        The list of proxies is cached on the proxy as proxy._proxies so
        that repeat calls will be faster.

        :param proxy: a replicated proxy
        """
        if self._query is None:
            self._query = self.getProxy('IceGrid/Query')
        if getattr(proxy, '_replicas', None) is None:
            proxy._replicas = [proxy.uncheckedCast(p) for p in self._query.findAllReplicas(proxy)]
        return proxy._replicas

    def serve(self):
        """Activates all adapters then waits for the shutdown signal.

        .. note:: This method is for server implementations only and is not
                  part of the environment interface.
        """
        for a in self._adapters.values():
            a.activate()
        self._communicator().waitForShutdown()

    def serverId(self):
        """Returns the ``Ice.Admin.ServerId`` property when called on a server."""
        ic = self._communicator()
        return ic.getProperties().getProperty('Ice.Admin.ServerId')
