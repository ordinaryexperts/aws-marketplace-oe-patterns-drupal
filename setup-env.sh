#!/usr/bin/env bash

echo "$(date): Starting setup-env.sh"

export CDK_VERSION=1.36.1
export PACKER_VERSION=1.5.5
export TASKCAT_VERSION=0.9.17

# system upgrades and tools
export DEBIAN_FRONTEND=noninteractive
apt-get -y -q -o=Dpkg::Use-Pty=0 update && apt-get -y -q -o=Dpkg::Use-Pty=0 upgrade
apt-get -y -q -o=Dpkg::Use-Pty=0 install curl unzip vim wget

# aws cli
cd /tmp
curl --silent --show-error https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip -o awscliv2.zip
unzip awscliv2.zip
./aws/install
cd -

# taskcat
apt-get -y -q -o=Dpkg::Use-Pty=0 install python3 python3-pip
pip3 install -q taskcat==$TASKCAT_VERSION

# cdk
apt-get -y -q -o=Dpkg::Use-Pty=0 install npm
npm install -g aws-cdk@$CDK_VERSION

# packer
wget -q -O /tmp/packer.zip https://releases.hashicorp.com/packer/$PACKER_VERSION/packer_${PACKER_VERSION}_linux_amd64.zip
unzip /tmp/packer.zip -d /usr/local/bin/
rm /tmp/packer.zip

echo "$(date): Finished setup-env.sh"
