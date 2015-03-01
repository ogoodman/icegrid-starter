import random
import Ice
from icecap import ibase
from icecap.base.util import pcall, pcall_f, call_f
from icecap.base.future import Future

HI = 2**63-1

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

    Returns (*master*, *priority*) of type (``proxy``, ``[int64]``).

    :param proxies: a list of proxies to query
    """
    return _chooseMaster(pcall(proxies, 'masterState'))

def findMaster_f(proxies):
    """Finds the master (or servant with highest priority) among the given proxies.

    Unreachable proxies are skipped and if the resulting list of proxies is empty
    ``None`` will be returned.

    Returns (*master*, *priority*) of type (``proxy``, ``[int64]``).

    :param proxies: a list of proxies to query
    """
    return pcall_f(proxies, 'masterState').then(_chooseMaster)

def _chooseMaster(master_info):
    """Selects the best master from a list of masterState results."""
    best_p = None
    max_priority = [-1]
    for p, priority, err in master_info:
        if err is not None:
            continue
        if best_p is None or priority > max_priority:
            best_p = p
            max_priority = priority
    return best_p, max_priority

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
    except (ibase.NotMaster, Ice.NoEndpointException):
        # Stale cached master or server offline.
        pass
    proxy._master = master = findMaster(env.replicas(proxy))[0]
    return getattr(master, method)(*args)

def mcall_f(env, proxy, method, *args):
    """Call the given method on the master.

    :param env: the environment
    :param proxy: a proxy for a ``MasterOrSlave`` replica group
    :param method: method to call (as a string)
    :param *args: arguments to pass
    """
    def set_master(master, priority):
        proxy._master = master
        return master

    def get_master():
        master = getattr(proxy, '_master', None)
        if master is None:
            master = env.replicas_f(proxy).then(findMaster_f).then(set_master)
        return master

    def retry(exc):
        return env.replicas_f(proxy).then(findMaster_f).then(set_master).then(call_f, method, *args)

    errors = (ibase.NotMaster, Ice.NoEndpointException)
    return Future(None).then(get_master).then(call_f, method, *args).catch(errors, retry)

class MasterOrSlave(ibase.MasterOrSlave):
    """A ``MasterOrSlave`` is a servant base class which tracks the
    information needed for a servant to manage its master/slave status.

    :param env: an environment
    """
    def __init__(self, env):
        self._env = env
        self._master_priority = random.randint(0, HI)
        self._is_master = False

    def masterState(self, curr=None):
        """Returns a list of *int64* giving the master priority of this replica.

        The first entry is 1 if this replica is the master, 0 otherwise.
        The second entry is a random number chosen at instantiation.

        When finding a master, priorities are compared lexicographically.
        If a replica is already a master, it will automatically come first.
        If no replica has yet become a master, the replica with the highest
        random number will be chosen.
        """
        return [1 if self._is_master else 0, self._master_priority]

    def findMaster_f(self):
        """Returns the master proxy from the configured replica group."""
        me, siblings = findLocal(self._env, self._proxy)
        if self._is_master:
            return Future(me)
        return findMaster_f(siblings).then(self._chooseMaster, me)

    def _chooseMaster(self, best_p, max_priority, me):
        """Chooses the best master between me or my best sibling."""
        if max_priority > self.masterState():
            return best_p
        if me is not None:
            self._is_master = True
        return me

    def assertMaster_f(self):
        """Raises ``NotMaster`` if this servant is not the master."""
        if self._is_master:
            return Future(None)
        return self.findMaster_f().then(self._assertMasterNow)

    def _assertMasterNow(self, _=None):
        """Raises ibase.NotMaster if I am not by now the confirmed master."""
        if not self._is_master:
            raise ibase.NotMaster()

    def isMaster_f(self):
        """Returns True if this is the master replica."""
        if self._is_master:
            return Future(True)
        return self.findMaster_f().then(lambda m: self._is_master)
