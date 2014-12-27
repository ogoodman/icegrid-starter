import os
from icecap.base.util import appRoot

INDEX_RST = """\
.. IceCap documentation master file

Welcome to IceCap's documentation
=================================

Contents:

.. toctree::
   :maxdepth: 2

%s
Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
"""

PACKAGE_RST = """\
.. IceCap documentation

%s - Another great package
%s========================

Contents:

.. toctree::
   :maxdepth: 2

%s"""

MODULE_RST = """\
.. IceCap documentation

%s - Another great module
%s=======================

.. automodule:: %s
   :members:
   :show-inheritance:
   :inherited-members:
"""

MOD_ROOT = os.path.join(appRoot(), 'python/icecap')
DOC_ROOT = os.path.join(appRoot(), 'doc/source')

EXCLUDE = ['icecap.config']

def allModules():
    pre_len = len(MOD_ROOT) - len('icecap')
    for path, dirs, files in os.walk(MOD_ROOT):
        for d in list(dirs):
            if d.startswith('.'):
                dirs.remove(d)
        if '__init__.py' not in files:
            continue
        for f in files:
            if f.endswith('.py') and f != '__init__.py' and not f.endswith('_test.py'):
                yield os.path.join(path, f)[pre_len:]

def main():
    mods = {}
    for f in allModules():
        mod = f[:-3].replace('/', '.')
        if mod in EXCLUDE:
            continue
        mods[mod] = None
        while '.' in mod:
            cmod = mod
            mod = mod.rsplit('.', 1)[0]
            if mod not in mods:
                mods[mod] = set()
            mods[mod].add(cmod)

    for mod, cmods in mods.iteritems():
        if cmods is not None:
            cmod_lines = ''.join(['   %s\n' % cmod for cmod in sorted(cmods)])
        if mod == 'icecap':
            outfile = 'index.rst'
            out = INDEX_RST % cmod_lines
        elif cmods is not None:
            outfile = mod + '.rst'
            out = PACKAGE_RST % (mod, '='*len(mod), cmod_lines)
        else:
            outfile = mod + '.rst'
            out = MODULE_RST % (mod, '='*len(mod), mod)

        outpath = os.path.join(DOC_ROOT, outfile)
        if not os.path.exists(outpath) or cmods is not None:
            with open(outpath, 'w') as fh:
                fh.write(out)
            print 'Added', outfile #, 'module' if cmods is None else 'package'

if __name__ == '__main__':
    main()
