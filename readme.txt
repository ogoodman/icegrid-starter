This project shows how to develop and deploy an IceGrid application.

There are two environments, a development environment hosted by
Vagrant, and a local production-like environment.

Development
===========

To use the development environment, review pillar/platform/dev.sls to
ensure that the IPs do not conflict with any existing hosts on your
local subnet. If they do, change them. Then do

  vagrant up

in order to obtain a fully provisioned two-node IceGrid grid.

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
server root. Assuming this project is in ~/icecap we can do

  sudo mkdir /srv
  sudo ln -s $HOME/icecap/salt/roots /srv/salt
  sudo ln -s $HOME/icecap/pillar /srv/pillar

Start the salt-master daemon (E.g. Ubuntu):

  sudo service salt-master start

Next we need to create some minions.

We will need the local IP of the salt master so that vagrant can add
an entry for the 'salt' host to the /etc/hosts file of each VM. 
(Use ifconfig to get your local network IP.)

  echo [your-ip] > local/master-ip

Review pillar/platform/local.sls to check that the IPs listed will not
cause any conflicts for you. Then,

  cd local
  vagrant up

to create a Salt minion. No further use is made of Vagrant in this
environment: it is simply a convenient means to create suitable local
VM images. 

For production deployments you must set up some hosts, provisioned as
Salt minions, and point them at the salt master. The Salt
configuration management abstraction ensures that there should be no
difference between administering the local environment or the
production one.

We connect the minion(s) with our master:

  sudo salt-key -L

should show us pending connections from all minions which are pointing
at our master.

  sudo salt-key -A

allows them all to connect. To check the connection, do:

  sudo salt '*' test.ping

In order to provision our servers (local or otherwise) we must provide
a little more configuration detail.

So that we can log into our servers:

  cp ~/.ssh/id_rsa.pub salt/roots

To authorize them to pull the application source code from our
repository, create the file pillar/passwords.sls containing svn
credentials for checking out this project:

  icecap_svn_repo: http://<svn-host>/svn/Projects/icecap
  icecap_svn_user: <svn-user>
  icecap_svn_password: <svn-password>

Finally, provision the server:

  sudo salt '*' state.highstate

Once that completes we should be able to log into the server via

  ssh icecap@icenode-1

Grid Services
=============

The icegridregistry is installed as upstart service ice-registry on
icebox-1. It starts automatically but it can be controlled via

  sudo initctl [start|stop|status] ice-registry

or (for production-like servers)

  sudo salt '*' service.[stop|start] ice-registry

Similarly icegridnode is installed as upstart service ice-node on all
nodes.

Node logs currently go to /var/log/upstart/ice-node.log on each host.
