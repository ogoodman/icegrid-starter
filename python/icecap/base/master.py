import random
from icecap.base.util import pcall

LO, HI = -2**63, 2**63-1

def findLocal(env, proxy):
    """Finds a local proxy in the replica group of *proxy*.

    Returns (*local*, *remotes*) where *local* is a proxy in the group on
    the server which this *env* belongs to, and *remote* is a list of the
    remaining proxies in the group.

    If *proxy* does not reside on the local server then *local* will be
    ``None`` and *remotes* will be the full list of replicas.

    :param env: environment resource factory
    :param proxy: a replica group proxy
    """
    server_id = env.server_id()
    proxies = env.replicas(proxy)
    local = None
    remote = []
    for p in proxies:
        if p.ice_getAdapterId().split('.', 1)[0] == server_id:
            local = p
        else:
            remote.append(p)
    return local, remote

def findMaster(proxies):
    """Finds the master (or servant with highest priority) among the given proxies.

    Unreachable proxies are skipped and if the resulting list of proxies is empty
    ``None`` will be returned.

    Returns (*master*, *is_master*, *priority*) of type (``proxy``, ``bool``, ``int64``).

    :param proxies: a list of proxies to query
    """
    items = zip(proxies, pcall(proxies, 'masterPriority'))
    best_p = None
    master = False
    max_priority = LO
    for p, mpi in items:
        result, err = mpi
        if err is not None:
            continue
        master, priority = result
        if best_p is None or master or priority > max_priority:
            best_p = p
            max_priority = priority
        if master:
            break
    return best_p, master, max_priority

class MasterInfo(object):
    """A ``MasterInfo`` is a helper which tracks the information needed for
    a servant to manage its master/slave status.

    :param env: an environment
    :param proxy: replica group proxy of the servant
    """
    def __init__(self, env, proxy):
        self._env = env
        self._proxy = proxy
        self._master_priority = random.randint(LO, HI) # TODO: in +/- 2**63.
        self._is_master = False

    def masterPriority(self, curr=None):
        """Returns the (*is_master*, *priority*) state of the local servant."""
        return (self._is_master, self._master_priority)

    def findMaster(self):
        """Returns the master proxy from the configured replica group."""
        me, siblings = findLocal(self._env, self._proxy)
        if self._is_master:
            return me
        best_p, master, max_priority = findMaster(siblings)
        if master or max_priority > self._master_priority:
            return best_p
        if me is not None:
            self._is_master = True
        return me

    def info(self, curr=None):
        return repr(self.findMaster())
