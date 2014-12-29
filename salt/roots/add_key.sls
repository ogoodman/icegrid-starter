# Add an authorized key to allow login as the application user.

# To actually do this, put a copy of the public key file into
#   salt/roots/id_rsa.pub
# and then do
#   salt '*' state.sls add_key
#
local_ssh:
  ssh_auth.present:
    - user: {{ pillar['userid'] }}
    - source: salt://id_rsa.pub
