# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  config.vm.box = "ubuntu/trusty32"

  config.ssh.forward_agent = true
  config.ssh.forward_x11 = true

  config.vm.synced_folder "salt/roots/", "/srv/salt/"

  config.vm.define "icebox-1" do |box|
    box.vm.hostname = "icebox-1"
    box.vm.network "public_network", ip: "192.168.1.101"
  end

  config.vm.define "icebox-3" do |box|
    box.vm.hostname = "icebox-3"
    box.vm.network "public_network", ip: "192.168.1.103"
  end

  config.vm.provision :salt do |salt|
    salt.minion_config = "salt/minion"
    salt.run_highstate = true
  end
end
