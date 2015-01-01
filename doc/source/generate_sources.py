"""Provides ``generateSources`` which generates a simple tree of contents pages."""

import os

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

def generateSources(project, contents):
    """Generates ``index.rst`` and a collection of contents pages.

    The input is a dictionary whose keys are the packages and
    modules to be documentend and whose values are the titles they
    should have in the generated contents pages.

    For each package or module ``a.b`` a corresponding file ``a.b.rst``
    will be generated in the current directory.

    :param project: project name
    :param contents: dictionary of module titles
    """
    mods = {}
    for mod in contents:
        if mod not in mods:
            mods[mod] = set()
        while '.' in mod:
            cmod = mod
            mod = mod.rsplit('.', 1)[0]
            if '.' not in mod:
                mod = 'index'
            if mod not in mods:
                mods[mod] = set()
            mods[mod].add(cmod)

    files = set()
    for mod, cmods in mods.iteritems():
        if cmods:
            cmod_lines = ''.join(['   %s\n' % cmod for cmod in sorted(cmods)])
        if mod != 'index':
            title = mod + ' - ' + contents[mod]
            title_lines = '%s\n%s' % (title, '=' * len(title))
        if mod == 'index':
            out = INDEX_RST % (project, project, cmod_lines)
        elif cmods:
            out = PACKAGE_RST % (project, title_lines, cmod_lines)
        else:
            out = MODULE_RST % (project, title_lines, mod)

        outfile = mod + '.rst'
        files.add(outfile)
        if os.path.exists(outfile):
            original = open(outfile).read()
        else:
            original = ''
        if original != out:
            with open(outfile, 'w') as fh:
                fh.write(out)
            print 'Added' if original == '' else 'Updated', outfile

    for file in os.listdir('.'):
        if file.endswith('.rst') and file not in files:
            os.unlink(file)
            print 'Removed', file

