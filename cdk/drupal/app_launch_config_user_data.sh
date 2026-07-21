#!/bin/bash

# CloudWatch agent
cat <<EOF > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json
{
  "agent": {
    "metrics_collection_interval": 60,
    "run_as_user": "root",
    "logfile": "/opt/aws/amazon-cloudwatch-agent/logs/amazon-cloudwatch-agent.log"
  },
  "metrics": {
    "metrics_collected": {
      "collectd": { "metrics_aggregation_interval": 60 },
      "disk": {
        "measurement": ["used_percent"],
        "metrics_collection_interval": 60,
        "resources": ["*"]
      },
      "mem": {
        "measurement": ["mem_used_percent"],
        "metrics_collection_interval": 60
      }
    },
    "append_dimensions": {
      "ImageId": "\${!aws:ImageId}",
      "InstanceId": "\${!aws:InstanceId}",
      "InstanceType": "\${!aws:InstanceType}",
      "AutoScalingGroupName": "\${!aws:AutoScalingGroupName}"
    }
  },
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          { "file_path": "/opt/aws/amazon-cloudwatch-agent/logs/amazon-cloudwatch-agent.log", "log_group_name": "${AsgSystemLogGroup}", "log_stream_name": "{instance_id}-/opt/aws/amazon-cloudwatch-agent/logs/amazon-cloudwatch-agent.log", "timezone": "UTC" },
          { "file_path": "/var/log/dpkg.log", "log_group_name": "${AsgSystemLogGroup}", "log_stream_name": "{instance_id}-/var/log/dpkg.log", "timezone": "UTC" },
          { "file_path": "/var/log/apt/history.log", "log_group_name": "${AsgSystemLogGroup}", "log_stream_name": "{instance_id}-/var/log/apt/history.log", "timezone": "UTC" },
          { "file_path": "/var/log/cloud-init.log", "log_group_name": "${AsgSystemLogGroup}", "log_stream_name": "{instance_id}-/var/log/cloud-init.log", "timezone": "UTC" },
          { "file_path": "/var/log/cloud-init-output.log", "log_group_name": "${AsgSystemLogGroup}", "log_stream_name": "{instance_id}-/var/log/cloud-init-output.log", "timezone": "UTC" },
          { "file_path": "/var/log/auth.log", "log_group_name": "${AsgSystemLogGroup}", "log_stream_name": "{instance_id}-/var/log/auth.log", "timezone": "UTC" },
          { "file_path": "/var/log/syslog", "log_group_name": "${AsgSystemLogGroup}", "log_stream_name": "{instance_id}-/var/log/syslog", "timezone": "UTC" },
          { "file_path": "/var/log/amazon/ssm/amazon-ssm-agent.log", "log_group_name": "${AsgSystemLogGroup}", "log_stream_name": "{instance_id}-/var/log/amazon/ssm/amazon-ssm-agent.log", "timezone": "UTC" },
          { "file_path": "/var/log/amazon/ssm/errors.log", "log_group_name": "${AsgSystemLogGroup}", "log_stream_name": "{instance_id}-/var/log/amazon/ssm/errors.log", "timezone": "UTC" },
          { "file_path": "/var/log/apache2/access.log", "log_group_name": "${AsgAppLogGroup}", "log_stream_name": "{instance_id}-/var/log/apache2/access.log", "timezone": "UTC" },
          { "file_path": "/var/log/apache2/error.log", "log_group_name": "${AsgSystemLogGroup}", "log_stream_name": "{instance_id}-/var/log/apache2/error.log", "timezone": "UTC" },
          { "file_path": "/var/log/apache2/access-ssl.log", "log_group_name": "${AsgAppLogGroup}", "log_stream_name": "{instance_id}-/var/log/apache2/access-ssl.log", "timezone": "UTC" },
          { "file_path": "/var/log/apache2/error-ssl.log", "log_group_name": "${AsgSystemLogGroup}", "log_stream_name": "{instance_id}-/var/log/apache2/error-ssl.log", "timezone": "UTC" }
        ]
      }
    },
    "log_stream_name": "{instance_id}"
  }
}
EOF
systemctl enable amazon-cloudwatch-agent
systemctl start amazon-cloudwatch-agent

# EFS mount
mkdir -p /mnt/efs
echo "${AppEfs}:/ /mnt/efs efs _netdev 0 0" >> /etc/fstab
mount -a

# First-boot Drupal copy: AMI ships /root/drupal; copy into EFS only on first boot.
#
# A tar-pipe (tar -cf - -C /root/drupal . | tar -xf -) was tried here to
# speed this up -- it doesn't help. The codebase is ~26k small files, and
# both cp -a and tar -xf still issue one open/write/close per file against
# the NFS-mounted EFS destination; the bottleneck is write-side per-file
# metadata ops on EFS, not read-side traversal on the source AMI disk, so
# batching the read side changes nothing. Measured ~14.5 min either way.
# Don't re-try this optimization without addressing the write-side cost
# instead (e.g. EFS Provisioned Throughput, fewer/larger files in the
# codebase, or a longer CreationPolicy timeout -- see below).
if [ ! -f /mnt/efs/drupal/index.php ]; then
  cp -a /root/drupal /mnt/efs/
  mkdir -p /mnt/efs/drupal/sites/default/files
  chown -R www-data:www-data /mnt/efs/drupal
  echo "Initial Drupal codebase copied to EFS."
fi

# Symlink Apache docroot at /var/www/app/drupal -> EFS
mkdir -p /var/www/app
rm -rf /var/www/app/drupal
ln -s /mnt/efs/drupal /var/www/app/drupal

# Write the OE Patterns Drupal pattern integration into sites/default/settings.local.php.
# Drupal's default settings.php (modified by packer) includes settings.local.php
# if it exists, which lets us populate $databases / $settings via separate
# assignments (NOT array literals) without tripping up Drupal's
# SettingsEditor::rewrite during site install. The PDO::MYSQL_ATTR_SSL_CA index
# is hardcoded to its integer value 1009 for the same reason.
cat <<'SETTINGS_LOCAL_EOF' > /mnt/efs/drupal/sites/default/settings.local.php
<?php

/**
 * OE Patterns Drupal pattern integration.
 * Written by EC2 user_data on each instance boot.
 */

$databases['default']['default']['driver'] = 'mysql';
$databases['default']['default']['database'] = 'drupal';
$databases['default']['default']['prefix'] = '';
$databases['default']['default']['collation'] = 'utf8mb4_general_ci';
$databases['default']['default']['namespace'] = 'Drupal\\mysql\\Driver\\Database\\mysql';
$databases['default']['default']['autoload'] = 'core/modules/mysql/src/Driver/Database/mysql/';
$databases['default']['default']['pdo'][1009] = '/opt/aws/rds/global-bundle.pem'; // PDO::MYSQL_ATTR_SSL_CA

if (file_exists('/opt/oe/patterns/drupal/secret.json')) {
  $secret = json_decode(file_get_contents('/opt/oe/patterns/drupal/secret.json'), TRUE);
  $databases['default']['default']['username'] = $secret['username'];
  $databases['default']['default']['password'] = $secret['password'];
}
if (file_exists('/opt/oe/patterns/drupal/db.json')) {
  $db = json_decode(file_get_contents('/opt/oe/patterns/drupal/db.json'), TRUE);
  $databases['default']['default']['host'] = $db['host'];
  $databases['default']['default']['port'] = $db['port'];
}

$settings['hash_salt'] = file_get_contents('/opt/oe/patterns/drupal/salt.txt');

// Memcached server registration. To use as the cache backend, run
// `drush en memcache -y` after the site is installed and add
//   $settings['cache']['default'] = 'cache.backend.memcache';
// in a separate file you include from here.
if (!defined('MAINTENANCE_MODE') && file_exists('/opt/oe/patterns/drupal/elasticache.json')) {
  $elasticache = json_decode(file_get_contents('/opt/oe/patterns/drupal/elasticache.json'), TRUE);
  $settings['memcache']['servers'] = [ $elasticache['host'] . ':' . $elasticache['port'] => 'default' ];
}

if (file_exists('/opt/oe/patterns/drupal/hostname.txt')) {
  $hostname = trim(file_get_contents('/opt/oe/patterns/drupal/hostname.txt'));
  $settings['trusted_host_patterns'] = ['^' . preg_quote($hostname) . '$'];
}
SETTINGS_LOCAL_EOF
chown www-data:www-data /mnt/efs/drupal/sites/default/settings.local.php
chmod 444 /mnt/efs/drupal/sites/default/settings.local.php

# Pattern runtime config (read by settings.local.php)
mkdir -p /opt/oe/patterns/drupal

SECRET_ARN="${DbSecretArn}"
echo "$SECRET_ARN" > /opt/oe/patterns/drupal/secret-arn.txt

SECRET_NAME=$(aws secretsmanager list-secrets --query "SecretList[?ARN=='$SECRET_ARN'].Name" --output text)
echo "$SECRET_NAME" > /opt/oe/patterns/drupal/secret-name.txt

aws ssm get-parameter \
    --name "/aws/reference/secretsmanager/$SECRET_NAME" \
    --with-decryption \
    --query Parameter.Value \
| jq -r . > /opt/oe/patterns/drupal/secret.json

# database
jq -n --arg host "${DbCluster.Endpoint.Address}" --arg port "${DbCluster.Endpoint.Port}" \
   '{host: $host, port: $port}' > /opt/oe/patterns/drupal/db.json

# memcached (always provisioned)
jq -n --arg host "${ElastiCacheCluster.ConfigurationEndpoint.Address}" --arg port "${ElastiCacheCluster.ConfigurationEndpoint.Port}" \
   '{host: $host, port: $port}' > /opt/oe/patterns/drupal/elasticache.json

# salt + hostname (resolved at synth time, written directly)
echo "${DrupalSalt}" > /opt/oe/patterns/drupal/salt.txt
echo "${Hostname}" > /opt/oe/patterns/drupal/hostname.txt

# db connect helper
cat <<'CONNECT_EOF' > /usr/local/bin/connect-to-db
#!/usr/bin/env bash
host=$(jq -r '.host' /opt/oe/patterns/drupal/db.json)
port=$(jq -r '.port' /opt/oe/patterns/drupal/db.json)
username=$(jq -r '.username' /opt/oe/patterns/drupal/secret.json)
password=$(jq -r '.password' /opt/oe/patterns/drupal/secret.json)
mysql -u "$username" -P "$port" -h "$host" --password="$password"
CONNECT_EOF
chmod 755 /usr/local/bin/connect-to-db

# permissions
chown -R www-data:www-data /opt/oe/patterns/drupal
chmod 600 /opt/oe/patterns/drupal/secret.json

# self-signed Apache cert (real cert is on the ALB)
openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
  -keyout /etc/ssl/private/apache-selfsigned.key \
  -out /etc/ssl/certs/apache-selfsigned.crt \
  -subj '/CN=localhost'
systemctl enable apache2 && systemctl start apache2

cfn-signal --exit-code $? --stack ${AWS::StackName} --resource Asg --region ${AWS::Region}
