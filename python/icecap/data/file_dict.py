import os

class FileDict(object):
    """Adapts a local file-system directory to a dict-of-strings interface.

    Usage::

        f = FileDict('/var/app/data')

        f['fred'] = 'Fred' # stores 'Fred' at 'fred'
        'fred' in f        # -> True
        f.keys()           # -> ['fred']
        del f['fred']      # next f['fred'] raises KeyError

    Because files are used for storage, keys must be usable as file paths and
    should not contains ``'..'`` or ``'/'``.

    :param path: a local directory path
    """
    def __init__(self, path):
        self._path = path

    def __getitem__(self, key):
        try:
            return open(os.path.join(self._path, key)).read()
        except IOError:
            raise KeyError(key)

    def __setitem__(self, key, value):
        assert '..' not in key and not key.startswith('/')
        if not os.path.exists(self._path):
            os.mkdir(self._path)
        with open(os.path.join(self._path, key), 'w') as out:
            out.write(value)

    def __delitem__(self, key):
        assert '..' not in key and not key.startswith('/')
        try:
            os.unlink(os.path.join(self._path, key))
        except OSError:
            pass

    def __contains__(self, key):
        return os.path.exists(os.path.join(self._path, key))

    def keys(self):
        """Returns a list of keys."""
        return os.listdir(self._path)
