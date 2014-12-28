#!py

import os
import yaml

# It would be handy if Salt gave you an easy way to include optional
# .sls files, but if it does, I couldn't find it. This is a
# work-around. If optional.sls exists, it is used; otherwise an empty
# dictionary is returned.

# NOTE: templating won't work inside 'optional.sls'.

def run():
    data = {}
    optfile = os.path.join(os.path.dirname(__file__), 'optional.sls')
    if os.path.exists(optfile):
        data = yaml.load(open(optfile))
    return data
