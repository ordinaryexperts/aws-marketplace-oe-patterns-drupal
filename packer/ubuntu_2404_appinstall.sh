#!/bin/bash -eux
# Packer's execute_command invokes this as `bash <path>`, which makes the
# shebang's flags a no-op. Re-enable errexit/nounset/xtrace explicitly so
# provisioning failures abort the build instead of silently shipping a
# broken AMI.
set -eux

SCRIPT_VERSION=1.10.3
SCRIPT_PREINSTALL=ubuntu_2204_2404_preinstall.sh
SCRIPT_POSTINSTALL=ubuntu_2204_2404_postinstall.sh

# preinstall steps (no CodeDeploy agent — Drupal 3.0.0 baked-into-AMI doesn't use CodePipeline)
curl -O "https://raw.githubusercontent.com/ordinaryexperts/aws-marketplace-utilities/$SCRIPT_VERSION/packer_provisioning_scripts/$SCRIPT_PREINSTALL"
chmod +x $SCRIPT_PREINSTALL
./$SCRIPT_PREINSTALL --install-efs-utils
rm $SCRIPT_PREINSTALL

#
# Drupal configuration
#  * https://www.drupal.org/docs/getting-started/system-requirements
#  * Codebase baked into /root/drupal; user_data copies to EFS on first boot.
#

DRUPAL_VERSION=11.3.8
PHP_VERSION=8.3

export DEBIAN_FRONTEND=noninteractive
export COMPOSER_ALLOW_SUPERUSER=1

# install Apache + PHP 8.3 + extensions Drupal needs
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
    php${PHP_VERSION}-uploadprogress \
    php${PHP_VERSION}-xml \
    php${PHP_VERSION}-zip \
    php-pear \
    unzip \
    zlib1g-dev

# install composer
EXPECTED_CHECKSUM=$(curl -sS https://composer.github.io/installer.sig)
curl -sS https://getcomposer.org/installer -o /tmp/composer-setup.php
ACTUAL_CHECKSUM=$(php -r "echo hash_file('sha384', '/tmp/composer-setup.php');")
if [ "$EXPECTED_CHECKSUM" != "$ACTUAL_CHECKSUM" ]; then
    echo "ERROR: composer installer checksum mismatch"
    exit 1
fi
php /tmp/composer-setup.php --install-dir=/usr/local/bin --filename=composer
rm /tmp/composer-setup.php

# install Drupal $DRUPAL_VERSION via composer (drupal/legacy-project layout — files at root)
mkdir -p /root/drupal
cd /root/drupal

cat <<COMPOSERJSON > composer.json
{
    "name": "fossoncloud/drupal",
    "description": "Drupal $DRUPAL_VERSION codebase baked into the FOSSonCloud AMI.",
    "type": "project",
    "license": "GPL-2.0-or-later",
    "repositories": [
        {
            "type": "composer",
            "url": "https://packages.drupal.org/8"
        }
    ],
    "require": {
        "composer/installers": "^2.3",
        "drupal/core-composer-scaffold": "^11.0",
        "drupal/core-project-message": "^11.0",
        "drupal/core-recommended": "$DRUPAL_VERSION",
        "drupal/core-vendor-hardening": "^11.0",
        "drupal/memcache": "^2.7",
        "drush/drush": "^13.5"
    },
    "minimum-stability": "stable",
    "prefer-stable": true,
    "config": {
        "sort-packages": true,
        "allow-plugins": {
            "composer/installers": true,
            "drupal/core-composer-scaffold": true,
            "drupal/core-project-message": true,
            "drupal/core-vendor-hardening": true,
            "drupal/core-recipe-unpack": true,
            "php-http/discovery": true,
            "symfony/runtime": true,
            "tbachert/spi": true
        }
    },
    "extra": {
        "drupal-scaffold": {
            "locations": {
                "web-root": "./"
            }
        },
        "installer-paths": {
            "core": ["type:drupal-core"],
            "libraries/{\$name}": ["type:drupal-library"],
            "modules/contrib/{\$name}": ["type:drupal-module"],
            "profiles/contrib/{\$name}": ["type:drupal-profile"],
            "themes/contrib/{\$name}": ["type:drupal-theme"],
            "drush/Commands/contrib/{\$name}": ["type:drupal-drush"],
            "modules/custom/{\$name}": ["type:drupal-custom-module"],
            "themes/custom/{\$name}": ["type:drupal-custom-theme"]
        }
    }
}
COMPOSERJSON

composer install --no-interaction --no-progress --prefer-dist

# settings.php is the vanilla scaffolded default + an explicit include of
# sites/default/settings.local.php (the default ships that include commented
# out). We write settings.local.php from user_data on each instance boot.
#
# settings.php is chmod'd read-only below. Drupal's own install wizard
# writes a literal $databases[...] array into settings.php via
# SettingsEditor::rewrite() as soon as the "Set up database" form is
# submitted -- even on a failed attempt, and even though it appends after
# our include block, so it silently overwrites the working credentials
# settings.local.php just set on every subsequent request. Since this
# pattern always ships working DB credentials via settings.local.php,
# settings.php never legitimately needs to be writable, so making it
# read-only up front prevents that whole failure class instead of
# tolerating "don't pre-populate $databases in settings.php" as a rule
# someone has to remember.
cp sites/default/default.settings.php sites/default/settings.php
cat <<'INCLUDE_EOF' >> sites/default/settings.php

if (file_exists($app_root . '/' . $site_path . '/settings.local.php')) {
  include $app_root . '/' . $site_path . '/settings.local.php';
}
INCLUDE_EOF
chmod 444 sites/default/settings.php

chown -R www-data:www-data /root/drupal

# configure apache
a2enmod php${PHP_VERSION}
a2enmod rewrite
a2enmod ssl
a2dissite 000-default
mkdir -p /var/www/app

cat <<'APACHE_EOF' > /etc/apache2/sites-available/drupal.conf
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

        # self-signed cert; real cert is managed by the ALB
        SSLEngine on
        SSLCertificateFile /etc/ssl/certs/apache-selfsigned.crt
        SSLCertificateKeyFile /etc/ssl/private/apache-selfsigned.key

        php_value memory_limit 256M
        php_value post_max_size 100M
        php_value upload_max_filesize 100M
</VirtualHost>
APACHE_EOF
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
