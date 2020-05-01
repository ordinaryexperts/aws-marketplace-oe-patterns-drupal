#!/usr/bin/env bash

export CDK_VERSION=1.36.1
export PACKER_VERSION=1.5.5
export TASKCAT_VERSION=0.9.17

export DEBIAN_FRONTEND=noninteractive
apt-get -y update && apt-get -y upgrade

# taskcat
apt-get -y install python3 python3-pip
pip3 install taskcat==$TASKCAT_VERSION

# cdk
apt-get -y install npm
npm install -g aws-cdk@$CDK_VERSION

# packer
apt-get -y install unzip wget
wget -O /tmp/packer.zip https://releases.hashicorp.com/packer/$PACKER_VERSION/packer_${PACKER_VERSION}_linux_amd64.zip
unzip /tmp/packer.zip -d /usr/local/bin/
rm /tmp/packer.zip
