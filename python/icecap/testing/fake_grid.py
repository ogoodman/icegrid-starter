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

    fred = cenv.get_proxy('fred@FooGroup')

By providing an interface identical to that of ``icecap.base.env.Env``
and a realistic simulation of the latter's behaviour we are able to
test code which might involve multiple interactions between servants
on the grid.

Note however that it is generally preferable to test servants in 
isolation and they should ideally be written so that this is possible.
"""

class FakeEnv(object):
    """Fake version of ``icecap.base.env.Env`` for use in tests.

    :param grid: a shared ``FakeGrid``
    :param server_id: the id of the server (if any) that this ``FakeEnv`` emulates
    """

    def __init__(self, grid, server_id='CLIENT'):
        self._grid = grid
        self._server_id = server_id

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

    def get_proxy(self, addr):
        """Obtain a proxy for a servant the shared grid.

        Usage::

            proxy = env.get_proxy('log@Log-node1.Log') # or
            proxy = env.get_proxy('log@LogGroup')

        Of course, the proxy will only be available from the replica
        group if it was provided as a member of that group.

        :param addr: proxy string with replica group or full adapter id
        """
        return FakeProxy(self._grid, addr)

    def replicas(self, proxy):
        """Returns a list containing all registered replicas of the proxy.

        The list of proxies is cached on the proxy as proxy._proxies.

        :param proxy: a replicated proxy
        """
        if not hasattr(proxy, '_replicas'):
            proxy._replicas = self._grid.replicas(proxy._addr)
        return proxy._replicas

class FakeGrid(object):
    """Fake version of an IceGrid grid, for use in testing."""

    def __init__(self):
        self._adapters = {}
        self._groups = {}

    def env(self, server_id='CLIENT'):
        """Returns a ``FakeEnv`` attached to this grid.

        The *server_id* forms part of the fully-qualified adapter-id::

            log = Logger()

            env = grid.env('Log-node1')
            env.provide('log', 'Log', log) # address is 'log@Log-node1.Log'

            e2 = grid.env('anything')
            log_proxy = e2.get_proxy('log@Log-node1.Log')

        :param server_id: server-id of the new ``FakeEnv``
        """
        return FakeEnv(self, server_id)

    def get_servant(self, addr, step=True):
        """Obtain a servant by its address.

        When getting a servant from a replicated adapter, each
        successive call will choose the next adapter, round-robin.

        Usage::

            log = grid.get_servant('log@Log-node1.Log') # or
            log = grid.get_servant('log@LogGroup')

        :para addr: proxy string for servant lookup
        """
        name, adapter = addr.split('@', 1)
        if adapter.endswith('Group'):
            grp = self._groups[adapter[:-5]]
            i, grp_l = grp
            assert len(grp_l) > 0
            adapter = grp_l[i % len(grp_l)]
            if step:
                grp[0] = i + 1
        return self._adapters[adapter][name]

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
            group = adapter[:-3].rsplit('.', 1)[-1]
            if group not in self._groups:
                self._groups[group] = [0, []]
            grp_l = self._groups[group][1]
            if adapter not in grp_l:
                grp_l.append(adapter)

    def proxy(self, addr):
        return FakeProxy(self, addr)

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

ATT_ERR_MSG = "'%s' object has no attribute '%s'" 

class FakeProxy(object):
    """Simulates an Ice proxy, passing calls through to the servant.

    :param grid: a ``FakeGrid``
    :param addr: a proxy string indicating a servant
    """
    def __init__(self, grid, addr):
        # We use double underscores to try to avoid name collisions
        # with random servant private methods.
        self._grid = grid
        self._addr = addr

    def _check_attr(self, name):
        """Raise an ``AttributeError`` if *name* cannot be called on this proxy.

        The attribute must correspond to a method of the servant
        and it may not contain underscores.

        :param name: the attribute to check
        """
        servant = self._servant(step=False)
        if '_' in name:
            raise AttributeError(ATT_ERR_MSG % (type(servant), name))
        method = getattr(servant, name)
        if not callable(method):
            raise AttributeError(ATT_ERR_MSG % (type(servant), name))

    def _servant(self, step=True):
        return self._grid.get_servant(self._addr, step)

    def _call(self, name, *args):
        return getattr(self._servant(), name)(*args)

    def __getattr__(self, name):
        # NOTE: we must get the servant on every call rather than saving
        # a bound method because it could change between calls.
        if name.startswith('begin_'):
            fname = name.split('_', 1)[-1]
            fun = lambda *args: args
        elif name.startswith('end_'):
            fname = name.split('_', 1)[-1]
            fun = lambda args: self._call(fname, *args)
        else:
            fname = name
            fun = lambda *args: self._call(name, *args)
        self._check_attr(fname)
        self.__dict__[name] = fun
        return fun

    def __repr__(self):
        return self._addr