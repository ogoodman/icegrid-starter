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
import IceGrid
import icegrid_config
from icecap.base.future import Future
from icecap.base.thread_pool import ThreadPool
from icecap.base.util import importSymbol, call_f
from icecap.base.env_base import EnvBase

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

class Env(EnvBase):
    """The core environment resource factory. Mediates access to all environment 
    resources such as files, Ice connections, HTTP requests, etc.

    .. note:: The current version only implements IceGrid connection methods.
    """
    def __init__(self):
        EnvBase.__init__(self)
        self._ic = None
        self._adapters = {}
        self._query = None
        self._work = ThreadPool(1)

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

    def do(self, func, *args, **kw):
        """Runs ``func(*args)`` in the work queue.

        The work queue is a single thread.

        :param func: a function to call
        :param args: arguments for *func*
        :param kw: keyword arguments for *func*
        """
        self._work.do(func, *args, **kw)

    def getProxy(self, addr, type=None, one_way=False):
        """Gets a proxy for the servant (if any) at the specified address.

        The servant is queried for its type and cast to the appropriate
        proxy type.

        The remote call is avoided if a proxy type is provided for an
        uncheckedCast. An instance of the same type can also be used.

        :param addr: proxy string for the required proxy
        :param type: type for the resulting proxy
        :param one_way: whether to return a one-way proxy
        """
        uproxy = self._communicator().stringToProxy(addr)
        if one_way:
            uproxy = uproxy.ice_oneway()
        if type is not None:
            return type.uncheckedCast(uproxy)
        return toMostDerived(uproxy)

    def grid(self):
        """Gets an associated grid admin object."""
        return Grid(self)

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

    def replicas(self, proxy, refresh=False):
        """Returns a list containing all registered replicas of the proxy.

        The list of proxies is cached on the proxy as proxy._proxies so
        that repeat calls will be faster.

        :param proxy: a replicated proxy
        """
        if self._query is None:
            self._query = self.getProxy('IceGrid/Query', IceGrid.QueryPrx)
        if refresh or not hasattr(proxy, '_replicas'):
            proxy._replicas = [proxy.uncheckedCast(p) for p in self._query.findAllReplicas(proxy)]
        return proxy._replicas

    def replicas_f(self, proxy, refresh=False):
        """Returns a list containing all registered replicas of the proxy.

        The list of proxies is cached on the proxy as proxy._proxies so
        that repeat calls will be faster.

        :param proxy: a replicated proxy
        """
        def set_replicas(replicas):
            proxy._replicas = [proxy.uncheckedCast(p) for p in replicas]
            return proxy._replicas
        if self._query is None:
            self._query = self.getProxy('IceGrid/Query', IceGrid.QueryPrx)
        if refresh or not hasattr(proxy, '_replicas'):
            return call_f(self._query, 'findAllReplicas', proxy).then(set_replicas)
        return Future(proxy._replicas)

    def serve(self):
        """Activates all adapters then waits for the shutdown signal.

        .. note:: This method is for server implementations only and is not
                  part of the environment interface.
        """
        for a in self._adapters.values():
            a.activate()
        self._runActivationCallbacks()
        self._communicator().waitForShutdown()

    def serverId(self):
        """Returns the ``Ice.Admin.ServerId`` property when called on a server."""
        ic = self._communicator()
        return ic.getProperties().getProperty('Ice.Admin.ServerId')

class _AdminProxy(object):
    """Acts as a proxy for the grid's IceGrid.Admin object.

    Takes care of transparently starting a new session if the
    previous one has expired.

    :param env: an ``Env`` environment instance
    """
    def __init__(self, env):
        self._env = env
        self._registry = None
        self._admin = None

    def _getAdmin(self, new_session=False):
        if self._registry is None:
            self._registry = self._env.getProxy('IceGrid/Registry')
        if self._admin is None or new_session:
            session = self._registry.createAdminSession('x', 'x')
            self._admin = session.getAdmin()
        return self._admin

    def __getattr__(self, name):
        def callWithSession(*args):
            try:
                return getattr(self._getAdmin(), name)(*args)
            except Ice.ObjectNotExistException:
                return getattr(self._getAdmin(new_session=True), name)(*args)
        return callWithSession

class Grid(object):
    """Administrative proxy for the grid.

    Usage::

        g = Grid(env)
        g.getAllServerIds()        # -> list of server ids
        g.stopServer('Demo-node1') # stops the specified server

    :param env: an ``Env`` environment instance
    """
    def __init__(self, env):
        self._env = env
        self._admin = _AdminProxy(env)

    def getAllAdapterIds(self):
        """Returns the adapter ids of all configured adapters."""
        return self._admin.getAllAdapterIds()

    def getAllServerIds(self):
        """Returns the server ids of all configured servers."""
        return self._admin.getAllServerIds()

    def serverIsActive(self, server_id):
        """Returns True if the server is currently active."""
        return self._admin.getServerState(server_id) == IceGrid.ServerState.Active

    def stopServer(self, server_id):
        """Stops a server.

        :param server_id: the server to stop
        """
        try:
            self._admin.stopServer(server_id)
        except IceGrid.ServerStopException:
            pass
