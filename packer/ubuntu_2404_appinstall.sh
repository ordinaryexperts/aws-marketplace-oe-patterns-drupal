#!/bin/bash -eux

SCRIPT_VERSION=1.6.0
SCRIPT_PREINSTALL=ubuntu_2204_2404_preinstall.sh
SCRIPT_POSTINSTALL=ubuntu_2204_2404_postinstall.sh

# preinstall steps
curl -O "https://raw.githubusercontent.com/ordinaryexperts/aws-marketplace-utilities/$SCRIPT_VERSION/packer_provisioning_scripts/$SCRIPT_PREINSTALL"
chmod +x $SCRIPT_PREINSTALL
./$SCRIPT_PREINSTALL --install-code-deploy-agent --install-efs-utils
rm $SCRIPT_PREINSTALL

#
# Drupal configuration
#  * https://www.drupal.org/docs/getting-started/system-requirements
#

DRUPAL_VERSION=11.3.8
PHP_VERSION=8.3

export DEBIAN_FRONTEND=noninteractive

# install Apache + PHP 8.3 + extensions Drupal needs
# Drupal core requires: date, dom, filter, gd, hash, json, pcre, PDO, session,
# SimpleXML, SPL, tokenizer, xml, zlib (json/hash/pcre/session/SPL/tokenizer
# are bundled in PHP 8.3 itself; the rest come from the listed extensions).
apt-get update
apt-get install -y \
    apache2 \
    libapache2-mod-php${PHP_VERSION} \
    mysql-client-8.0 \
    mysql-client-core-8.0 \
    nfs-common \
    php${PHP_VERSION} \
    php${PHP_VERSION}-apcu \
    php${PHP_VERSION}-cli \
    php${PHP_VERSION}-curl \
    php${PHP_VERSION}-dev \
    php${PHP_VERSION}-fpm \
    php${PHP_VERSION}-gd \
    php${PHP_VERSION}-intl \
    php${PHP_VERSION}-mbstring \
    php${PHP_VERSION}-memcached \
    php${PHP_VERSION}-mysql \
    php${PHP_VERSION}-opcache \
    php${PHP_VERSION}-xml \
    php${PHP_VERSION}-zip \
    php-pear \
    zlib1g-dev

# uploadprogress PECL extension
printf "\n" | pecl install uploadprogress
echo "extension=uploadprogress.so" > /etc/php/${PHP_VERSION}/apache2/conf.d/20-uploadprogress.ini
echo "extension=uploadprogress.so" > /etc/php/${PHP_VERSION}/cli/conf.d/20-uploadprogress.ini

# configure apache
a2enmod php${PHP_VERSION}
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

        php_value memory_limit 256M
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

        # self-signed cert; real cert is managed by the ELB
        SSLEngine on
        SSLCertificateFile /etc/ssl/certs/apache-selfsigned.crt
        SSLCertificateKeyFile /etc/ssl/private/apache-selfsigned.key

        php_value memory_limit 256M
        php_value post_max_size 100M
        php_value upload_max_filesize 100M
</VirtualHost>
EOF
a2ensite drupal

# apache2 will be enabled / started on boot via user_data
systemctl disable apache2

# install RDS SSL CA bundle for Aurora MySQL TLS connections
mkdir -p /opt/aws/rds
curl -fsSL https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem \
    -o /opt/aws/rds/global-bundle.pem

# postinstall steps (AMI hardening, cleanup)
curl -O "https://raw.githubusercontent.com/ordinaryexperts/aws-marketplace-utilities/$SCRIPT_VERSION/packer_provisioning_scripts/$SCRIPT_POSTINSTALL"
chmod +x $SCRIPT_POSTINSTALL
./$SCRIPT_POSTINSTALL
rm $SCRIPT_POSTINSTALL
