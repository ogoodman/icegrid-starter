#!/usr/bin/python

"""Script to add, update, list or remove the grid application.

Usage::

    grid_admin.py [add|update|list|remove|show-xml]

* add: adds or updates the grid application
* update: updates the application (assumes it is already loaded)
* list: lists all loaded applications
* remove: removes the grid application
* show-xml: shows the generated XML without updating anything

The application configuration is generated from from ``application.yml``
and ``piller/platform/*.sls``.

Each service corresponds to an executable Ice server. The ``application.yml``
file should have a ``services`` entry whose value is a list of service
descriptions, and an ``application`` entry whose value is the application name.

Each service must define (string) values for the following keys:

* name: name of the service from which adapter ids are generated
* runs: path of the executable, relative to the APP_ROOT

The following additional keys are optional:

* replicated: may be True, False or (the string) both
* nodes: may be a node id (string) or list of node ids

If ``replicated`` is False or absent, an adapter with id equal to the name is
generated. This means that the full adapter id on a given node is 
``<name>-<node>.<name>``, e.g. ``Printer-node2.Printer``.

If ``replicated`` is True, an adapter-id of the form ``<name>Rep`` is
generated so that the full adapter id on a given node is
``<name>-<node>.<name>Rep``, e.g. ``Printer-node2.PrinterRep``.
Furthermore the adapter is added to an adapter-group of ``<name>Group``.

If ``replicated`` is ``both``, both of the above adapters are generated.

When ``nodes`` is not specified, the service is generated on all nodes.
If ``nodes`` is a node id, the service is generated on that node only,
while if it is a list of node ids it is generated for just those nodes.
"""

import os
import sys
import yaml

from icegrid_config import ICE_REG_HOST

APP_ROOT = os.path.abspath(__file__).rsplit('/', 2)[0]
PLATFORM_SLS = os.path.join(APP_ROOT, 'pillar/platform')
GRID_XML_PATH = os.path.join(APP_ROOT, 'grid/grid.xml')
CLIENT_CFG = os.path.join(APP_ROOT, 'grid/client.cfg')

APP_CONF = yaml.load(open(os.path.join(APP_ROOT, 'application.yml')))
APP_NAME = APP_CONF['application']

ADMIN_CMD = "icegridadmin --Ice.Config=%s -ux -px -e '%%s'" % CLIENT_CFG

APP_FRAG = """\
<icegrid>
  <application name="%s">
%s%s  </application>
</icegrid>
"""

NODE_FRAG = """
    <node name="%s">
%s    </node>
"""

ADAPTER_FRAG = """\
        <adapter name="%(name)s" endpoints="tcp"/>
"""

REPL_ADAPTER_FRAG = """\
        <adapter name="%(name)sRep" replica-group="%(name)sGroup" endpoints="tcp"/>
"""

SERVER_FRAG = """\
      <server id="%(name)s-%(node)s" exe="%(run)s" activation="on-demand">
%(opt)s%(adapter)s      </server>
"""

OPT_FRAG = """\
        <option>%s</option>
"""

GROUP_FRAG = """\
    <replica-group id="%sGroup">
      <load-balancing type="round-robin" />
    </replica-group>
"""

def doAdmin(cmd):
    return os.system(ADMIN_CMD % cmd)

def queryAdmin(cmd):
    return os.popen(ADMIN_CMD % cmd)

def gridXML():
    hosts = {}
    for name in os.listdir(PLATFORM_SLS):
        if not name.endswith('.sls'):
            continue
        try:
            config = yaml.load(open(os.path.join(PLATFORM_SLS, name)))
            if config['registry'] == ICE_REG_HOST:
                hosts.update(config['hosts'])
        except Exception, e:
            print >>sys.stderr, 'Warning: exception %e loading %s' % (e, name)

    groups_xml = []

    services = APP_CONF['services']
    for service in services:
        args = service.get('args', [])
        if isinstance(args, basestring):
            args = [args]
        if 'setup' in service:
            assert 'run' not in service, "Service %(name)s may specify only one of 'setup' or 'run'" % service
            service['run'] = 'servers/gen_server.py'
            args.insert(0, service['setup'])
        if service['run'].endswith('.py'):
            args.insert(0, service['run'])
            service['run'] = 'python'
        if isinstance(service.get('nodes'), basestring):
            service['nodes'] = [service['nodes']]
        adapter_xml = []
        if service.get('replicated') in (None, False, 'both'):
            adapter_xml.append(ADAPTER_FRAG % service)
        if service.get('replicated') in (True, 'both'):
            adapter_xml.append(REPL_ADAPTER_FRAG % service)
            groups_xml.append(GROUP_FRAG % service['name'])

        opts = [OPT_FRAG % arg for arg in args]
        service['adapter'] = ''.join(adapter_xml)
        service['opt'] = ''.join(opts)

    node_xml = []
    for hostname in sorted(hosts):
        node = 'node' + hostname.rsplit('-', 1)[-1]
        server_xml = []
        for service in services:
            nodes = service.get('nodes')
            if nodes is not None and node not in nodes:
                continue
            service['node'] = node
            server_xml.append(SERVER_FRAG % service)
        node_xml.append(NODE_FRAG % (node, ''.join(server_xml)))

    return APP_FRAG % (APP_NAME, ''.join(groups_xml), ''.join(node_xml))

def writeGridXML():
    xml = gridXML()
    with open(GRID_XML_PATH, 'w') as out:
        out.write(xml)

def main():
    if 'add' in sys.argv[1:]:
        apps = [l.strip() for l in queryAdmin('application list')]
        what = 'update' if APP_NAME in apps else 'add'
        writeGridXML()
        doAdmin('application %s %s' % (what, GRID_XML_PATH))
    elif 'update' in sys.argv[1:]:
        writeGridXML()
        doAdmin('application update %s' % GRID_XML_PATH)
    elif 'list' in sys.argv[1:]:
        for l in queryAdmin('application list'):
            print l.strip()
    elif 'remove' in sys.argv[1:]:
        doAdmin('application remove %s' % APP_NAME)
    elif 'show-xml' in sys.argv[1:]:
        print gridXML(),

if __name__ == '__main__':
    main()
