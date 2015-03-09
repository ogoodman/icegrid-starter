"""A ``FakeGrid`` allows you to test your grid clients, servants and servers
in a deep and realistic manner.

Usage::

    grid = FakeGrid()

    # mimic Env() on server 'Foo' on 'node1'
    env = grid.env('Foo-node1')

    from icecap.servers.my_server import serverSetup
    serverSetup(env)

    # make a client env.
    cenv = grid.env()

    fred = cenv.getProxy('fred@FooGroup')

By providing an interface identical to that of ``icecap.base.env.Env``
and a realistic simulation of the latter's behaviour we are able to
test code which might involve multiple interactions between servants
on the grid.

Note however that it is generally preferable to test servants in 
isolation and they should ideally be written so that this is possible.
"""

import os
import re
import shutil
import sys
import traceback
import Ice
from icecap.base.env_base import EnvBase
from icecap.base.future import Future, argTupToRv, rvToArgTup

DATA_DIR = '/tmp/fake_grid_data'

class FakeEnv(EnvBase):
    """Fake version of ``icecap.base.env.Env`` for use in tests.

    :param grid: a shared ``FakeGrid``
    :param server_id: the id of the server (if any) that this ``FakeEnv`` emulates
    """

    def __init__(self, grid, server_id=''):
        EnvBase.__init__(self)
        self._grid = grid
        self._server_id = server_id
        self._data_dir = None

    def dataDir(self):
        """Returns the local data directory path."""
        if self._data_dir is None:
            node_id = self._server_id.rsplit('-', 1)[-1]
            assert node_id != '', 'Only servers have a data directory.'
            # Make sure tests don't destroy real data.
            assert '..' not in node_id and not node_id.startswith('/')
            self._data_dir = os.path.join(self._grid.dataDir(), node_id)
            if not os.path.exists(self._data_dir):
                os.mkdir(self._data_dir)
        return self._data_dir

    def do(self, func, *args, **kw):
        """Runs func(*args) in the work queue.

        The work queue is a single thread.

        :param func: a function to call
        :param args: arguments for *func*
        """
        func(*args, **kw)

    def getProxy(self, addr, type=None, one_way=False):
        """Obtain a proxy for a servant the shared grid.

        Usage::

            proxy = env.getProxy('log@Log-node1.Log') # or
            proxy = env.getProxy('log@LogGroup')

        Of course, the proxy will only be available from the replica
        group if it was provided as a member of that group.

        :param addr: proxy string with replica group or full adapter id
        :param type: type for the resulting proxy
        :param one_way: whether to return a one-way proxy
        """
        return FakeProxy(self._grid, addr, one_way)

    def grid(self):
        """Get the associated ``FakeGrid``."""
        return self._grid

    def provide(self, name, adapter, servant):
        """Provide a servant on the shared grid.

        Usage::

            env = grid.env('Log-node1')

            env.provide('log', 'Log', log)    # provides 'log@Log-node1.Log'
            env.provide('log', 'LogRep', log) # provides 'log@LogGroup'

        :param name: name for the servant
        :param adapter: adapter id
        :param servant: the servant to provide
        """
        a_id = '%s.%s' % (self._server_id, adapter)
        self._grid.provide(name, a_id, servant)
        addr = name + '@' + (adapter[:-3]+'Group' if adapter.endswith('Rep') else a_id)
        servant._proxy = self.getProxy(addr)

    def replicas(self, proxy, refresh=False):
        """Returns a list containing all registered replicas of the proxy.

        The list of proxies is cached on the proxy as proxy._proxies.

        :param proxy: a replicated proxy
        """
        if refresh or not hasattr(proxy, '_replicas'):
            proxy._replicas = self._grid.replicas(proxy._addr)
        return proxy._replicas

    def replicas_f(self, proxy, refresh=False):
        """Returns a list containing all registered replicas of the proxy.

        The list of proxies is cached on the proxy as proxy._proxies so
        that repeat calls will be faster.

        :param proxy: a replicated proxy
        """
        return Future(self.replicas(proxy, refresh))

    def serverId(self):
        """Returns the server-id of this ``FakeEnv``."""
        return self._server_id

class FakeGrid(object):
    """Fake version of an IceGrid grid, for use in testing."""

    def __init__(self):
        self._adapters = {}
        self._groups = {}
        self._servers = {}
        self._data_dir = None
        self._disabled = set()

    def add_group_member(self, server_id):
        """Adds this server id to the appropriate replica group.

        .. note:: it does not really matter whether such a replica
            group really exists: if it does not, servants will never
            be provided on the required adapters so any attempt to
            use the group will fail anyway.

        :param server_id: the id of the server which might provide replicas
        """
        group = server_id.split('-', 1)[0]
        adapter = '%s.%sRep' % (server_id, group)
        if group not in self._groups:
            self._groups[group] = [0, []]
        grp_l = self._groups[group][1]
        if adapter not in grp_l:
            grp_l.append(adapter)

    def addServer(self, server_id, setup_func):
        """Sets the specified server up to start on-demand.

        :param server_id: the server id of the server
        :param setup_func: function to call when the server starts
        """
        self._servers[server_id] = setup_func
        self.add_group_member(server_id)

    def dataDir(self):
        """Returns the local data directory path."""
        if self._data_dir is None:
            if os.path.exists(DATA_DIR):
                shutil.rmtree(DATA_DIR)
            os.mkdir(DATA_DIR)
            self._data_dir = DATA_DIR
        return DATA_DIR

    def disable(self, server_id):
        """Disables a server.

        A disabled server will not start when sent a request and will
        instead cause an Ice.NoEndpointException to be raised.

        :param server_id: the server to disable
        """
        self._disabled.add(server_id)

    def enable(self, server_id):
        """Enables a previously disabled server.

        Example::

            grid.enable('Demo-node2')

        :param server_id: the server to enable
        """
        self._disabled.discard(server_id)

    def env(self, server_id=''):
        """Returns a ``FakeEnv`` attached to this grid.

        The *server_id* forms part of the fully-qualified adapter-id::

            log = Logger()

            env = grid.env('Log-node1')
            env.provide('log', 'Log', log) # address is 'log@Log-node1.Log'

            e2 = grid.env('anything')
            log_proxy = e2.getProxy('log@Log-node1.Log')

        :param server_id: server-id of the new ``FakeEnv``
        """
        return FakeEnv(self, server_id)

    def getAllAdapterIds(self):
        """Returns all possible adapter ids of the installed servers."""
        ids = []
        for server_id in self._servers:
            name = server_id.split('-', 1)[0]
            ids.append('%s.%s' % (server_id, name))
            ids.append('%s.%sRep' % (server_id, name))
        for name in self._groups:
            ids.append('%sGroup' % name)
        return ids

    def getAllServerIds(self):
        """Returns the server ids of all installed servers."""
        return self._servers.keys()

    def get_servant(self, addr, step=True):
        """Obtain a servant by its address.

        When getting a servant from a replicated adapter, each
        successive call will choose the next adapter, round-robin.

        Usage::

            log = grid.get_servant('log@Log-node1.Log') # or
            log = grid.get_servant('log@LogGroup')

        :param addr: proxy string for servant lookup
        """
        name, adapter = addr.split('@', 1)
        if adapter.endswith('Group'):
            grp = self._groups[adapter[:-5]]
            i, grp_l = grp
            assert len(grp_l) > 0
            adapter = grp_l[i % len(grp_l)]
            if step:
                grp[0] = i + 1
        if adapter not in self._adapters:
            server_id = adapter.split('.', 1)[0]
            if server_id in self._disabled:
                raise Ice.NoEndpointException(addr)
            if server_id in self._servers:
                env = self.env(server_id)
                self._servers[server_id](env)
                env._runActivationCallbacks()
        ad = self._adapters[adapter]
        try:
            return ad[name]
        except KeyError:
            raise Ice.ObjectNotExistException(Ice.Identity(name))

    def provide(self, name, adapter, servant):
        """Put a servant onto the given adapter with the specified name.

        The full server-id qualified adapter-id is required, as in
        ``Log-node1.Log`` rather than just ``Log``.

        If the adapter-id ends with ``'Rep'`` the corresponding group
        is updated at the same time.

        Usage::

            grid.provide('log', 'Log-node1.LogRep', log)

        :param name: name to use for the servant
        :param adapter: full adapter-id on which to provide the servant
        :param servant: the servant to provide
        """
        if adapter not in self._adapters:
            self._adapters[adapter] = {}
        self._adapters[adapter][name] = servant

        if adapter.endswith('Rep'):
            self.add_group_member(adapter.split('.', 1)[0])

    def proxy(self, addr):
        return FakeProxy(self, addr, one_way=False)

    def replicas(self, addr):
        """Returns a list containing all registered replicas of the proxy.

        The list of proxies is cached on the proxy as proxy._proxies.

        :param addr: a proxy string
        """
        name, adapter = addr.split('@')
        if not adapter.endswith('Group'):
            return []
        adapters = self._groups.get(adapter[:-5], [0, []])[-1]
        return [self.proxy('%s@%s' % (name, a)) for a in adapters]

    def serverIsActive(self, server_id):
        """Returns True if the server is currently active."""
        for a_id in self._adapters:
            if server_id == a_id.split('.', 1)[0]:
                return True
        return False

    def stopServer(self, server_id):
        """Removes all adapters added by the specified server.

        :param server_id: the server to stop
        """
        a_name = server_id.split('-', 1)[0]
        self._adapters.pop('%s.%s' % (server_id, a_name), None)
        self._adapters.pop('%s.%sRep' % (server_id, a_name), None)

ATT_ERR_MSG = "'%s' object has no attribute '%s'" 

class FakeCB(object):
    def __init__(self):
        self._result = None
        self._exc = None

    def ice_response(self, *args):
        self._result = args

    def ice_exception(self, exc):
        self._exc = exc

    def value(self):
        if type(self._result) is tuple:
            return argTupToRv(self._result)
        assert self._exc is not None, 'FakeCB is unresolved'
        raise self._exc

    def discard(self):
        if type(self._result) is tuple:
            return
        assert self._exc is not None, 'FakeCB is unresolved'
        _onewayExc(self._exc)

class FakeResult(object):
    def __init__(self, result, exc):
        self._result = result
        self._exc = exc

    def _end(self):
        if self._exc is None:
            return self._result
        raise self._exc

TOO_MANY_ARGS_RE = re.compile(r'\w+\(\) takes (at most|exactly) \d+ arguments')

def _onewayExc(exc):
    print >>sys.stderr, 'OneWay Exc:', exc

class FakeProxy(object):
    """Simulates an Ice proxy, passing calls through to the servant.

    :param grid: a ``FakeGrid``
    :param addr: a proxy string indicating a servant
    """
    def __init__(self, grid, addr, one_way):
        self._grid = grid
        self._addr = addr
        self._one_way = one_way

    def _check_attr(self, name):
        """Raise an ``AttributeError`` if *name* cannot be called on this proxy.

        The attribute must correspond to a method of the servant
        and it may not contain underscores.

        :param name: the attribute to check
        """
        try:
            servant = self._servant(step=False)
        except Ice.ObjectNotExistException:
            if self._one_way:
                return
            raise
        if '_' in name:
            raise AttributeError(ATT_ERR_MSG % (type(servant), name))
        for n in (name, name + '_async'):
            if callable(getattr(servant, n, None)):
                break
        else:
            raise AttributeError(ATT_ERR_MSG % (type(servant), name))

    def _servant(self, step=True):
        """Gets the servant to which this proxy points.

        :param step: whether to step to the next servant (if replicated)
        """
        return self._grid.get_servant(self._addr, step)

    def _call(self, name, *args):
        try:
            servant = self._servant()
        except Ice.ObjectNotExistException:
            if self._one_way:
                return
            raise
        method = getattr(servant, name + '_async', None)
        if method is not None:
            cb = FakeCB()
            try:
                method(cb, *args)
            except Exception, e:
                cb.ice_exception(e)
            if self._one_way:
                cb.discard()
            return cb.value()
        method = getattr(servant, name)
        if self._one_way:
            try:
                method(*args)
            except Exception, e:
                _onewayExc(e)
            return
        return method(*args)

    def _begin(self, fname, args):
        if len(args) >= 2 and callable(args[-2]) and callable(args[-1]):
            # We have been passed callbacks
            cb, eb = args[-2:]
            try:
                result = self._call(fname, *args[:-2])
                cb(*rvToArgTup(result))
            except Exception, e:
                eb(e)
        else:
            try:
                return FakeResult(self._call(fname, *args), None)
            except Exception, e:
                return FakeResult(None, e)

    def __getattr__(self, name):
        # NOTE: we must get the servant on every call rather than saving
        # a bound method because it could change between calls.
        if name.startswith('begin_'):
            fname = name.split('_', 1)[-1]
            fun = lambda *args: self._begin(fname, args)
        elif name.startswith('end_'):
            fname = name.split('_', 1)[-1]
            fun = lambda result: result._end()
        else:
            fname = name
            fun = lambda *args: self._call(name, *args)
        if not name.startswith('begin_'):
            self._check_attr(fname)
        self.__dict__[name] = fun
        return fun

    def __repr__(self):
        return self._addr

    def ice_getAdapterId(self):
        """Gets the adapter-id part of this proxy's address.

        E.g. the adapter-id of proxy ``'printer@Printer-node1.Printer'`` 
        is ``'Printer-node1.Printer'``.
        """
        return self._addr.split('@', 1)[-1]

    def ice_getIdentity(self):
        """Gets the Ice.Identity of this proxy.

        This is a simple structure with ``name`` and ``category`` attributes.
        """
        return Ice.Identity(self._addr.split('@', 1)[0], '')
