#!/bin/sh

echo "$1 salt" >> /etc/hosts

add-apt-repository -y ppa:saltstack/salt
apt-get update
apt-get -y install salt-minion
