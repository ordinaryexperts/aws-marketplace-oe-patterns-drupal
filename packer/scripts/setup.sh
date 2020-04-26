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

# install CloudWatch agent
cd /tmp
curl https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb -o amazon-cloudwatch-agent.deb
dpkg -i -E ./amazon-cloudwatch-agent.deb
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

# configure apache
a2enmod rewrite
a2enmod ssl

a2dissite 000-default
cat <<EOF > /etc/apache2/sites-available/app.conf
<VirtualHost *:80>
        ServerAdmin webmaster@localhost
        DocumentRoot /var/www/html

        LogLevel warn
        ErrorLog /var/log/apache2/error.log
        CustomLog /var/log/apache2/access.log combined

        RewriteEngine On
        RewriteOptions Inherit

        <Directory /var/www/html>
            Options Indexes FollowSymLinks MultiViews
            AllowOverride All
            Require all granted
        </Directory>

        AddType application/x-httpd-php .php
        AddType application/x-httpd-php phtml pht php
</VirtualHost>
<VirtualHost *:443>
        ServerAdmin webmaster@localhost
        DocumentRoot /var/www/html

        LogLevel warn
        ErrorLog /var/log/apache2/error-ssl.log
        CustomLog /var/log/apache2/access-ssl.log combined

        RewriteEngine On
        RewriteOptions Inherit

        <Directory /var/www/html>
            Options Indexes FollowSymLinks MultiViews
            AllowOverride All
            Require all granted
        </Directory>

        AddType application/x-httpd-php .php
        AddType application/x-httpd-php phtml pht php

        # self-signed cert
        # real cert is managed by the ELB
        SSLEngine on
        SSLCertificateFile /etc/ssl/certs/apache-selfsigned.crt
        SSLCertificateKeyFile /etc/ssl/private/apache-selfsigned.key
</VirtualHost>
EOF
a2ensite app

# apache2 will be enabled / started on boot
systemctl disable apache2

# apt cleanup
apt-get -y autoremove
apt-get -y update
