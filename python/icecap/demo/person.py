class Person(object):
    """A ``Person`` is a simple serializable object.

    The ``'name'`` and ``'dob'`` are preserved by serialization, while the
    ``'env'`` parameter (unused in this example) can be provided by the
    *extra* dictionary of a ``CapDict``.

    :param name: the person's name
    :param dob: the person's date of birth
    :param env: an (unused) environment
    """

    serialize = ('name', 'dob')

    def __init__(self, name, dob, env=None):
        self._name = name
        self._dob = dob
        self._env = env

    def __str__(self):
        return 'name: %(_name)s, dob: %(_dob)s' % self.__dict__
