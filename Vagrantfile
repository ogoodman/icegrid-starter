# -*- mode: ruby -*-
# vi: set ft=ruby :

require 'yaml'
pillar = YAML.load_file('pillar/platform/dev.sls')

Vagrant.configure("2") do |config|
  config.vm.box = "ubuntu/trusty32"

  config.ssh.forward_agent = true
  config.ssh.forward_x11 = true

  config.vm.synced_folder "salt/roots/", "/srv/salt/"

  pillar["hosts"].each do |hostname, ip|
    config.vm.define hostname do |box|
      box.vm.hostname = hostname
      box.vm.network "public_network", ip: ip
    end
  end

  config.vm.provision :salt do |salt|
    salt.pillar(pillar)

    salt.minion_config = "salt/minion"
    salt.run_highstate = true
  end
end
