#!/bin/bash -eux

# wait for cloud-init to be done
$IN_DOCKER || cloud-init status --wait

# apt upgrade
export DEBIAN_FRONTEND=noninteractive
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
# collectd for metrics
apt-get -y install collectd

# install CodeDeploy agent - requires ruby
apt-get -y install ruby
cd /tmp
curl https://aws-codedeploy-us-west-1.s3.us-west-1.amazonaws.com/latest/install -o install
chmod +x ./install
./install auto
cd -

# install efs mount helper - requires git
apt-get -y install bin-utils git
git clone https://github.com/aws/efs-utils /tmp/efs-utils
cd /tmp/efs-utils
./build-deb.sh
apt-get install -y ./build/amazon-efs-utils*deb
cd -

# install apache and php
apt-get -y install            \
        apache2               \
        libapache2-mod-php7.2 \
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
        php7.2-xml            \
        zlib1g-dev

# memcache
printf "\n" | pecl install memcache
echo "extension=memcache.so" > /etc/php/7.2/apache2/conf.d/20-memcache.ini
echo "extension=memcache.so" > /etc/php/7.2/cli/conf.d/20-memcache.ini

# configure apache
a2enmod rewrite
a2enmod ssl

a2dissite 000-default
mkdir -p /var/www/app/drupal
cat <<EOF > /etc/apache2/sites-available/drupal.conf
LogFormat "{\"time\":\"%{%Y-%m-%d}tT%{%T}t.%{msec_frac}tZ\", \"process\":\"%D\", \"filename\":\"%f\", \"remoteIP\":\"%a\", \"host\":\"%V\", \"request\":\"%U\", \"query\":\"%q\", \"method\":\"%m\", \"status\":\"%>s\", \"userAgent\":\"%{User-agent}i\", \"referer\":\"%{Referer}i\"}" cloudwatch
ErrorLogFormat "{\"time\":\"%{%usec_frac}t\", \"function\":\"[%-m:%l]\", \"process\":\"[pid%P]\", \"message\":\"%M\"}"

<VirtualHost *:80>
        ServerAdmin webmaster@localhost
        DocumentRoot /var/www/app/drupal

        LogLevel warn
        ErrorLog /var/log/apache2/error.log
        CustomLog /var/log/apache2/access.log cloudwatch

        RewriteEngine On
        RewriteOptions Inherit

        <Directory /var/www/app/drupal>
            Options Indexes FollowSymLinks MultiViews
            AllowOverride All
            Require all granted
        </Directory>

        AddType application/x-httpd-php .php
        AddType application/x-httpd-php phtml pht php

        php_value memory_limit 128M
        php_value post_max_size 100M
        php_value upload_max_filesize 100M
</VirtualHost>
<VirtualHost *:443>
        ServerAdmin webmaster@localhost
        DocumentRoot /var/www/app/drupal

        LogLevel warn
        ErrorLog /var/log/apache2/error-ssl.log
        CustomLog /var/log/apache2/access-ssl.log cloudwatch

        RewriteEngine On
        RewriteOptions Inherit

        <Directory /var/www/app/drupal>
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

        php_value memory_limit 128M
        php_value post_max_size 100M
        php_value upload_max_filesize 100M
</VirtualHost>
EOF
a2ensite drupal

# apache2 will be enabled / started on boot
systemctl disable apache2

# apt cleanup
apt-get -y autoremove
apt-get -y update
