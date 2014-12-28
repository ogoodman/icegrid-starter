# {% set node = 'node' + grains['id'].rsplit('-')[-1] %}
# {% set node_cfg = pillar['app_root'] + '/grid/' + node + '.cfg' %}
# {% set client_cfg = pillar['app_root'] + '/grid/client.cfg' %}

{{ client_cfg }}:
  file.managed:
    - source: salt://ice-client-tpl.cfg
    - template: jinja
    - user: {{ pillar['userid'] }}
    - group: {{ pillar['userid'] }}
    - makedirs: True

{{ node_cfg }}:
  file.managed:
    - source: salt://ice-node-tpl.cfg
    - template: jinja
    - user: {{ pillar['userid'] }}
    - group: {{ pillar['userid'] }}
    - makedirs: True

{{ pillar['data_root'] }}/node:
  file.directory:
    - user: {{ pillar['userid'] }}
    - group: {{ pillar['userid'] }}
    - makedirs: True

/etc/init/ice-node.conf:
  file.managed:
    - source: salt://ice-node-tpl.conf
    - template: jinja

ice-node:
  service.running:
    - require:
      - file: /etc/init/ice-node.conf
