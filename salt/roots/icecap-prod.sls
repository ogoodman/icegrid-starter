subversion:
  pkg.installed

icecap:
  user.present:
    - fullname: IceCap user
    - uid: 1010
    - home: /home/icecap
    - shell: /bin/bash

icecap_ssh:
  ssh_auth.present:
    - user: icecap
    - source: salt://id_rsa.pub
    - require:
      - user: icecap

mewlip:
  host.present:
    - ip: 192.168.1.6

http://mewlip/svn/Projects/icecap:
  svn.latest:
    - target: /home/icecap/app
    - user: icecap
    - username: icecap
    - password: {{ pillar['icecap_svn_password'] }}
    - require:
      - user: icecap
      - host: mewlip

/home/icecap/.bashrc:
  file.append:
    - text: export PYTHONPATH=/home/icecap/app/python
    - require:
      - user: icecap

/home/icecap/app/python/icecap/config.py:
  file.symlink:
    - target: config_prod.py
    - user: icecap
    - require:
      - svn: http://mewlip/svn/Projects/icecap

