#!/bin/bash -eux

# Apt upgrade
apt -y update && apt-get -y upgrade

# Install latest CFN utilities
python /usr/lib/python2.7/dist-packages/easy_install.py https://s3.amazonaws.com/cloudformation-examples/aws-cfn-bootstrap-latest.tar.gz

# Apt cleanup.
apt -y autoremove
apt -y update
