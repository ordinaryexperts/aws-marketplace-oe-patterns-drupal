#!/bin/bash -eux

# wait for cloud-init to be done
cloud-init status --wait

# apt upgrade
apt-get -y update && apt-get -y upgrade

# install helpful utilities
apt-get -y install curl git jq ntp unzip vim wget zip

# install latest CFN utilities
apt-get -y install python-pip
pip install https://s3.amazonaws.com/cloudformation-examples/aws-cfn-bootstrap-latest.tar.gz

# install aws cli
cd /tmp
curl https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip -o awscliv2.zip
unzip awscliv2.zip
./aws/install
cd -

# install apache and php
apt-get -y install            \
        apache2               \
        mysql-client-5.7      \
        mysql-client-core-5.7 \
        nfs-common            \
        php-mysql             \
        php7.2                \
        php7.2-cgi            \
        php7.2-curl           \
        php7.2-dev            \
        php7.2-gd             \
        php7.2-mbstring       \
        php7.2-xml

# apt cleanup
apt-get -y autoremove
apt-get -y update
