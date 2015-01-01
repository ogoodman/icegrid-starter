{% if pillar['userid'] != 'vagrant' %}
# Make a user to run IceGrid services.
{{ pillar['userid'] }}:
  user.present:
    - fullname: IceGrid user
    - uid: {{ pillar.get('uid', 1010) }}
    - home: /home/{{ pillar['userid'] }}
    - shell: /bin/bash
{% endif %}

# Check the source code out if necessary.

{% if 'svn_repo' in pillar %}
# Check the source out using svn.
subversion:
  pkg.installed

{% if 'svn_host' in pillar %}
{{ pillar['svn_host']['name'] }}:
  host.present:
    - ip: {{ pillar['svn_host']['ip'] }}
{% endif %}

{{ pillar['svn_repo'] }}:
  svn.latest:
    - target: {{ pillar['app_root'] }}
    - user: {{ pillar['userid'] }}
    - username: {{ pillar['svn_user'] }}
    - password: {{ pillar['svn_password'] }}
    - require:
{% if 'svn_host' in pillar %}
      - host: {{ pillar['svn_host']['name'] }}
{% endif %}
{% if pillar['userid'] != 'vagrant' %}
      - user: {{ pillar['userid'] }}
{% endif %}

{% elif 'git_repo' in pillar %}
# Check the source out using git
git:
  pkg.installed

{{ pillar['git_repo'] }}:
  git.latest:
    - target: {{ pillar['app_root'] }}
    - user: {{ pillar['userid'] }}
    - rev: {{ pillar.get('git_branch', 'master') }}
    - require:
      - pkg: git
{% if pillar['userid'] != 'vagrant' %}
      - user: {{ pillar['userid'] }}
{% endif %}
{% endif %}

# Generate the platform configuration file.
{{ pillar['app_root'] }}/python/icegrid_config.py:
  file.managed:
    - source: salt://config-tpl.py
    - user: {{ pillar['userid'] }}
    - group: {{ pillar['userid'] }}
    - template: jinja
{% if 'svn_repo' in pillar %}
    - require:
      - svn: {{ pillar['svn_repo'] }}
{% elif 'git_repo' in pillar %}
    - require:
      - git: {{ pillar['git_repo'] }}
{% endif %}

# Set PYTHONPATH to the app_root/python directory.
/home/{{ pillar['userid'] }}/.bashrc:
  file.append:
    - text: export PYTHONPATH={{ pillar['app_root'] }}/python
{% if pillar['userid'] != 'vagrant' %}
    - require:
      - user: {{ pillar['userid'] }}
{% endif %}

# Build the project.
make:
  cmd.run:
    - cwd: {{ pillar['app_root'] }}
    - user: {{ pillar['userid'] }}
    - env:
      - PYTHONPATH: {{ pillar['app_root'] }}/python
    - require:
      - file: {{ pillar['app_root'] }}/python/icegrid_config.py

{{ pillar['data_root'] }}:
  file.directory:
    - user: {{ pillar['userid'] }}
    - group: {{ pillar['userid'] }}
    - makedirs: True
