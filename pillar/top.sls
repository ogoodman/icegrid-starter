base:
  'icebox-*':
    - platform.dev
  'icenode-*':
    - platform.local
  '*':
    # Load optional.sls if present, else nothing.
    - get_optional
