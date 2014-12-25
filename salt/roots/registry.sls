{% if pillar['registry'] == pillar['hosts'][grains['id']] %}
{{ pillar['data_root'] }}/registry/master:
  file.directory:
    - user: {{ pillar['userid'] }}
    - group: {{ pillar['userid'] }}
    - makedirs: True

/etc/init/ice-registry.conf:
  file.managed:
    - source: salt://ice-registry-tpl.conf
    - template: jinja

ice-registry:
  service.running:
    - require:
      - file: /etc/init/ice-registry.conf
{% endif %}
    