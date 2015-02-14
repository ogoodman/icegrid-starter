import random
from icecap import ibase
from icecap.base.util import pcall, pcall_f
from icecap.base.future import Future

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
    server_id = env.serverId()
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
    return _chooseMaster(pcall(proxies, 'masterState'))

def findMaster_f(proxies):
    """Finds the master (or servant with highest priority) among the given proxies.

    Unreachable proxies are skipped and if the resulting list of proxies is empty
    ``None`` will be returned.

    Returns (*master*, *is_master*, *priority*) of type (``proxy``, ``bool``, ``int64``).

    :param proxies: a list of proxies to query
    """
    return pcall_f(proxies, 'masterState').then(_chooseMaster)

def _chooseMaster(master_info):
    """Selects the best master from a list of masterState results."""
    best_p = None
    master = False
    max_priority = LO
    for p, result, err in master_info:
        if err is not None:
            continue
        master, priority = result
        if best_p is None or master or priority > max_priority:
            best_p = p
            max_priority = priority
        if master:
            break
    return best_p, master, max_priority

def mcall(env, proxy, method, *args):
    """Call the given method on the master.

    :param env: the environment
    :param proxy: a proxy for a ``MasterOrSlave`` replica group
    :param method: method to call (as a string)
    :param *args: arguments to pass
    """
    master = getattr(proxy, '_master', None)
    if master is None:
        # No cached master: find the master now.
        proxy._master = master = findMaster(env.replicas(proxy))[0]
    try:
        return getattr(master, method)(*args)
    except ibase.NotMaster:
        # Probably a stale cached master.
        pass
    proxy._master = master = findMaster(env.replicas(proxy))[0]
    return getattr(master, method)(*args)

class MasterOrSlave(ibase.MasterOrSlave):
    """A ``MasterOrSlave`` is a servant base class which tracks the
    information needed for a servant to manage its master/slave status.

    :param env: an environment
    """
    def __init__(self, env):
        self._env = env
        self._master_priority = random.randint(LO, HI)
        self._is_master = False

    def masterState(self, curr=None):
        """Returns the pair (*is_master, priority*) of type (``bool``, ``int64``).

        The rule is that if one of the servants returns ``True`` for
        *is_master*, that one is the master. If none return ``True``
        the servant which returned the highest *priority* is master
        (and will start returning ``True`` for *is_master* as soon as
        it accepts the next call for which it must be master).
        """
        return (self._is_master, self._master_priority)

    def findMaster_f(self):
        """Returns the master proxy from the configured replica group."""
        me, siblings = findLocal(self._env, self._proxy)
        if self._is_master:
            return Future(me)
        return findMaster_f(siblings).then(self._chooseMaster, me)

    def _chooseMaster(self, best_p, master, max_priority, me):
        """Chooses the best master between me or my best sibling."""
        if master or max_priority > self._master_priority:
            return best_p
        if me is not None:
            self._is_master = True
        return me

    def assertMaster_f(self):
        """Raises ``NotMaster`` if this servant is not the master."""
        if self._is_master:
            return Future(True)
        return self.findMaster_f().then(self._assertMasterNow)

    def _assertMasterNow(self, _=None):
        """Raises ibase.NotMaster if I am not by now the confirmed master."""
        if not self._is_master:
            raise ibase.NotMaster()
