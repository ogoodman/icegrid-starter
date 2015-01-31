import os
import sys
import traceback
from cStringIO import StringIO

def appRoot():
    """Returns the top-level application directory."""
    return os.path.abspath(__file__).rsplit('/', 4)[0]

def getAddr(prx):
    """Gets the address (proxy string) from a proxy or proxy string.

    Accepts both proxies and proxy strings so the caller may
    handle both transparently.

    :param prx: a proxy or proxy string
    """
    if not isinstance(prx, basestring):
        return str(prx)
    if type(prx) is unicode:
        return prx.encode('utf8')
    return prx

def getNode(prx):
    """Gets the node from a proxy or proxy string.

    :param prx: a proxy or proxy string
    """
    addr = getAddr(prx)
    return addr.split('@', 1)[-1].split('.', 1)[0].rsplit('-', 1)[-1]

def getReplicaAddr(prx, node):
    """Gets the proxy string for a replica of *prx* on the specified node.

    The specified proxy or proxy string must be a replica group proxy
    of the form ``<id>@<adapter>Group`` with replicas of the form
    ``<id>@<adapter>-<node>.<adapter>Rep``.
 
    :param prx: a proxy or proxy string
    """
    name, group = getAddr(prx).split('@', 1)
    assert group.endswith('Group')
    adapter = group[:-5]
    return '%s@%s-%s.%sRep' % (name, adapter, node, adapter)

def grabOutput(func, *args):
    """Calls ``func(*args)`` capturing and returning stdout and stderr.

    :param func: a function to call
    :param args: arguments for *func*
    """
    ko, ke = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = StringIO(), StringIO()
    try:
        func(*args)
    except:
        traceback.print_exc()
    o, e = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = ko, ke
    return o.getvalue(), e.getvalue()

def importSymbol(import_name):
    """Dynamically imports the specified object.

    :param import_name: the dotted import path
    """
    mod_name, symbol = import_name.rsplit('.', 1)
    module = __import__(mod_name, fromlist = [symbol])
    return getattr(module, symbol)

def openLocal(env, path, mode='r'):
    """Opens a file in the local data directory.

    Takes care of creating any directories required in the process.

    :param env: the environment
    :param path: path under the data directory
    :param mode: mode in which to open the file
    """
    assert not path.startswith('/') and '..' not in path
    f_path = os.path.join(env.dataDir(), path)
    f_dir = os.path.dirname(f_path)
    if not os.path.exists(f_dir):
        os.makedirs(f_dir)
    return open(f_path, mode)

def pcall(proxies, method, *args):
    """Makes a given method call in parallel on all the supplied proxies.

    Returns a list of ``(result, exc)`` for each proxy respectively. If no
    exception was raised, ``exc`` will be ``None``. If an exception was
    raised, ``result`` will be None.

    :param proxies: list of proxies to call
    :param method: the method to call
    :param args: arguments to provide with the call
    """
    rs = [(p, getattr(p, 'begin_' + method)(*args)) for p in proxies]
    results = []
    for p, r in rs:
        try:
            result = getattr(p, 'end_' + method)(r)
            results.append((result, None))
        except Exception, e:
            results.append((None, e))
    return results
