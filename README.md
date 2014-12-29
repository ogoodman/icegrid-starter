IceGrid starter
===============

This project shows how to develop and deploy an IceGrid application.

There are two environments: a development environment managed by
Vagrant, and a local production-like environment.

Development
===========

To use the development environment, review `pillar/platform/dev.sls` to
ensure that the IPs do not conflict with any existing hosts on your
local subnet. If they do, change them. Then do

    vagrant up

in order to obtain a fully provisioned and running two-node grid.

The GUI admin tool
==================

IceGrid comes with a nice graphical user interface for inspecting and
managing your grid. See:

  http://doc.zeroc.com/display/Ice/Getting+Started+with+IceGrid+Admin

for full details.

The development provisioning process will copy this tool
(`IceGridGUI-3.5.1.jar`) into the project root. From there you should be able to run it via:

    java -jar IceGridGUI-3.5.1.jar &

To connect with your registry:

 * Choose File > Login.. (or click on the icon with the green up-arrow)
 * Click on 'New Connection'
 * Choose 'Direct'
 * Enter an instance name of 'IceGrid'
 * Choose 'hostname and port number' for the addressing information
 * Enter your registry IP (192.168.1.21 if you didn't have to change it)
 * Enter 'x' for username and password and click finish to connect.

The tool saves your connection details so the process is a bit quicker
the next time around.

You can use the node context-menu items 'Retrieve stdout' and
'Retrieve stderr' to view all server output.

NOTE: due to buffering `stdout` output is not always visible immediately.

Local and Production
====================

To use the local production-like environment, a few steps are
necessary.

First, we install the Salt master on the local host. For full details
on setting up a Salt master and connecting minions see:

  http://docs.saltstack.com/en/latest/topics/tutorials/walkthrough.html

E.g. on Ubuntu:

    sudo add-apt-repository ppa:saltstack/salt
    sudo apt-get update
    sudo apt-get install salt-master

Add our salt and pillar directories to the salt master's file
server root. Assuming this project is in `~/icegrid` we can do

    sudo mkdir /srv
    sudo ln -s $HOME/icegrid/salt/roots /srv/salt
    sudo ln -s $HOME/icegrid/pillar /srv/pillar

Start the `salt-master` daemon (E.g. Ubuntu):

    sudo service salt-master start

Next we need to create some minions.

Review `pillar/platform/local.sls` to check that the IPs listed will
not cause any conflicts for you. Then,

    cd local
    vagrant up

to create two Salt minions. No further use is made of Vagrant in this
environment: it is simply a convenient means to create suitable local
VM images.

For production deployments you must set up some hosts, provisioned as
Salt minions, and point them at the salt master. The Salt
configuration management abstraction ensures that there should be no
difference between administering the local environment or the
production one.

We connect the minions with our master:

    sudo salt-key -L

should show us pending connections from all minions which are pointing
at our master.

    sudo salt-key -A

allows them to connect. To check the connection, do:

    sudo salt '*' test.ping

Finally, provision the server:

    sudo salt '*' state.highstate

If you want to be able to log into the local servers using your SSH
key, do

    cp ~/.ssh/id_rsa.pub salt/roots
    sudo salt '*' state.sls add_key

Grid Services
=============

The icegridregistry is installed as upstart service `ice-registry` on
`icebox-1`. It starts automatically but it can be controlled via

    sudo service ice-registry [start|stop|status]

or (for production-like servers)

    sudo salt '*' service.[stop|start] ice-registry

Similarly icegridnode is installed as upstart service `ice-node` on all
nodes.

