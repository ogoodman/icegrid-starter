import os

APP_ROOT = os.path.abspath(__file__).rsplit('/', 2)[0]
MOD_ROOT = os.path.join(APP_ROOT, 'python')
DOC_ROOT = os.path.join(APP_ROOT, 'doc/source')
CONTENTS = os.path.join(APP_ROOT, 'doc/contents.txt')

INDEX_RST = """\
.. %s documentation master file

Welcome to %s's documentation
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
.. %s documentation

%s

Contents:

.. toctree::
   :maxdepth: 2

%s"""

MODULE_RST = """\
.. %s documentation

%s

.. automodule:: %s
   :members:
   :show-inheritance:
   :inherited-members:
"""

def allModules():
    pre_len = len(MOD_ROOT) + 1
    for path, dirs, files in os.walk(MOD_ROOT):
        for d in list(dirs):
            if d.startswith('.'):
                dirs.remove(d)
        if '__init__.py' not in files:
            continue
        for f in files:
            if f.endswith('.py') and f != '__init__.py' and not f.endswith('_test.py'):
                yield os.path.join(path, f)[pre_len:-3].replace('/', '.')

def main():
    if not os.path.exists(CONTENTS):
        return
    contents = {}
    for l in open(CONTENTS):
        l = l.strip()
        if l.startswith('#') or l == '':
            continue
        mod, title = l.split(None, 1)
        contents[mod] = title

    project = contents.pop('project')

    mods = {}
    for mod in allModules():
        if mod not in contents:
            continue
        mods[mod] = None
        while '.' in mod:
            cmod = mod
            mod = mod.rsplit('.', 1)[0]
            if '.' not in mod:
                mod = 'index'
            if mod not in mods:
                mods[mod] = set()
            mods[mod].add(cmod)

    for mod, cmods in mods.iteritems():
        if cmods is not None:
            cmod_lines = ''.join(['   %s\n' % cmod for cmod in sorted(cmods)])
        if mod != 'index':
            title = mod + ' - ' + contents[mod]
            title_lines = '%s\n%s' % (title, '=' * len(title))
        if mod == 'index':
            out = INDEX_RST % (project, project, cmod_lines)
        elif cmods is not None:
            out = PACKAGE_RST % (project, title_lines, cmod_lines)
        else:
            out = MODULE_RST % (project, title_lines, mod)

        outfile = mod + '.rst'
        outpath = os.path.join(DOC_ROOT, outfile)
        if os.path.exists(outpath):
            original = open(outpath).read()
        else:
            original = ''
        if original != out:
            with open(outpath, 'w') as fh:
                fh.write(out)
            print 'Updated', outfile
        else:
            print 'Unchanged', outfile

if __name__ == '__main__':
    main()
