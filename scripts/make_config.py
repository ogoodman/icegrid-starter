import os
import sys
from icecap import config

TEMPLATE = {}

TEMPLATE['registry.cfg'] = """\
IceGrid.Registry.Client.Endpoints=tcp -p 4061
IceGrid.Registry.Server.Endpoints=tcp
IceGrid.Registry.Internal.Endpoints=tcp
IceGrid.Registry.AdminPermissionsVerifier=IceGrid/NullPermissionsVerifier
IceGrid.Registry.Data=%(DATA_ROOT)s/registry/master
IceGrid.Registry.DynamicRegistration=1
"""

TEMPLATE['client.cfg'] = """\
Ice.Default.Locator=IceGrid/Locator:tcp -h %(ICE_REG_HOST)s -p 4061
"""

config = TEMPLATE[sys.argv[1]] % config.__dict__

out_file = sys.argv[2]

with open(out_file, 'w') as out:
    out.write(config)
