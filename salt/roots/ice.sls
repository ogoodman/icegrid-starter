ice_repo:
  pkgrepo.managed:
    - name: deb http://www.zeroc.com/download/Ice/3.5/ubuntu trusty-zeroc main
    - file: /etc/apt/sources.list.d/ice3.5-trusty.list
    - key_url: http://www.zeroc.com/download/RPM-GPG-KEY-zeroc-release
    - require_in:
      - pkg: icegrid
      - pkg: ice-dev

icegrid:
  pkg.installed

ice-dev:
  pkg.installed
