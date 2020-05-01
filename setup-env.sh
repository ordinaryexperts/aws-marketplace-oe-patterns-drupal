#!/usr/bin/env bash

export CDK_VERSION=1.36.1
export TASKCAT_VERSION=0.9.17

export DEBIAN_FRONTEND=noninteractive
apt-get -y update

# taskcat
apt-get -y install python3 python3-pip
pip3 install taskcat==$TASKCAT_VERSION

# cdk
apt-get -y install npm
npm install -g aws-cdk@$CDK_VERSION
