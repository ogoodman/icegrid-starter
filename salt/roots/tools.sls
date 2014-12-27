python-pip:
  pkg.installed

nose:
  pip.installed:
    - require:
      - pkg: python-pip

coverage:
  pip.installed:
    - require:
      - pkg: python-pip

Sphinx:
  pip.installed:
    - require:
      - pkg: python-pip
