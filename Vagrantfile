# -*- mode: ruby -*-
# vi: set ft=ruby :

require 'yaml'

options = File.exist?('vagrant.yml')? YAML.load_file('vagrant.yml'): Hash.new

Vagrant.configure("2") do |config|

    config.vm.provider "virtualbox" do |v|
        v.memory = options["memory"] ||= 2042
        v.cpus = options["cpus"] ||= 1
    end

    name = "ubuntu"

    config.vm.define name do |machine|

        machine.vm.box = "ubuntu/trusty64"
        machine.vm.box_url = "https://app.vagrantup.com/ubuntu/boxes/trusty64"

        machine.vm.provision "base", type: "shell" do |shell|
            shell.path = "infra/bbox/bbox_update.sh"
        end
    end
end