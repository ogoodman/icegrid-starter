import os
import sys
import traceback
from cStringIO import StringIO

def appRoot():
    """Returns the top-level application directory."""
    return os.path.abspath(__file__).rsplit('/', 4)[0]

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
