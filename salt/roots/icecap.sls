# Ensure the icecap user is present.
{% if pillar['userid'] != 'vagrant' %}
{{ pillar['userid'] }}:
  user.present:
    - fullname: IceCap user
    - uid: 1010
    - home: /home/{{ pillar['userid'] }}
    - shell: /bin/bash

# Add an authorized key.
icecap_ssh:
  ssh_auth.present:
    - user: {{ pillar['userid'] }}
    - source: salt://id_rsa.pub
    - require:
      - user: {{ pillar['userid'] }}
{% endif %}

# Check the source code out if necessary.
{% if pillar['svn_checkout'] %}
subversion:
  pkg.installed

{% if 'icecap_svn_host' in pillar %}
{{ pillar['icecap_svn_host']['name'] }}:
  host.present:
    - ip: {{ pillar['icecap_svn_host']['ip'] }}
{% endif %}

{{ pillar['icecap_svn_repo'] }}:
  svn.latest:
    - target: {{ pillar['app_root'] }}
    - user: {{ pillar['userid'] }}
    - username: {{ pillar['icecap_svn_user'] }}
    - password: {{ pillar['icecap_svn_password'] }}
    - require:
{% if 'icecap_svn_host' in pillar %}
      - host: {{ pillar['icecap_svn_host']['name'] }}
{% endif %}
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
{% if 'icecap_svn_host' in pillar %}
    - require:
      - svn: {{ pillar['icecap_svn_repo'] }}
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
