#!/usr/bin/env bash

export CDK_VERSION=1.36.1
export PACKER_VERSION=1.5.5
export TASKCAT_VERSION=0.9.17

# system upgrades and tools
export DEBIAN_FRONTEND=noninteractive
apt-get -y update && apt-get -y upgrade
apt-get -y install curl unzip vim wget

# aws cli
cd /tmp
curl https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip -o awscliv2.zip
unzip awscliv2.zip
./aws/install
cd -

# taskcat
apt-get -y install python3 python3-pip
pip3 install taskcat==$TASKCAT_VERSION

# cdk
apt-get -y install npm
npm install -g aws-cdk@$CDK_VERSION

# packer
wget -O /tmp/packer.zip https://releases.hashicorp.com/packer/$PACKER_VERSION/packer_${PACKER_VERSION}_linux_amd64.zip
unzip /tmp/packer.zip -d /usr/local/bin/
rm /tmp/packer.zip
