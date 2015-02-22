import simplejson as json
import weakref
from icecap.base.util import importSymbol

class CapDict(object):
    """A dictionary of serializable objects.

    For an object to be serializable it must 

    * have a class attribute of ``'serialize'`` consisting of a tuple of names (strings),
    * a constructor whose parameters include all names in the ``'serialize'`` tuple,
    * and which assigns each argument unchanged to a member whose name is ``'_' + <name>``.

    Additional parameters may be present; each extra name must be a key of the ``extra`` 
    argument of the CapDict used to store instances.

    Usage::

        d = CapDict(FileDict(path), extra={'env': env})
        d['fred'] = Person(env=env, name='Fred', age=42) # Person must be serializable

        f = d['fred']         # -> a Person(env=env, name='Fred', age=42)
        'fred' in d           # -> True
        d.keys()              # -> ['fred']
        del d['fred']         # removes 'fred'

        d.get('fred', barney) # -> d['fred'] if 'fred' is present, else barney.

    :param store: a dict-like object capable of storing strings
    :param extra: a dict of additional arguments to supply when deserializing
    :param cache: a dict-like object in which to cache instantiated objects
    """
    def __init__(self, store, extra=None, cache=None):
        self._store = store
        self._cache = weakref.WeakValueDictionary() if cache is None else cache
        self._extra = {} if extra is None else extra

    def __getitem__(self, id):
        try:
            return self._cache[id]
        except KeyError:
            info = json.loads(self._store[id])
            info.update(self._extra)
            cls = importSymbol(info.pop('CLS'))
            inst = object.__new__(cls)
            inst._save = lambda i: self.__setitem__(id, i)
            inst.__init__(**info)
            self._cache[id] = inst
            return inst

    def __setitem__(self, id, inst):
        info = dict([(k, inst.__dict__['_'+k]) for k in inst.serialize])
        cls = type(inst)
        info['CLS'] = '%s.%s' % (cls.__module__, cls.__name__)
        self._store[id] = json.dumps(info)
        self._cache[id] = inst
        inst._save = lambda i: self.__setitem__(id, i)

    def __delitem__(self, id):
        inst = self._cache.pop(id, None)
        if inst is not None:
            inst._savefn = None
        try:
            del self._store[id]
        except KeyError:
            pass

    def __contains__(self, id):
        return id in self._store

    def keys(self):
        return self._store.keys()

    def get(self, id, default=None):
        try:
            return self[id]
        except KeyError:
            return default
