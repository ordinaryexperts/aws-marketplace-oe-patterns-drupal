#!/bin/bash

# aws cloudwatch
cat <<EOF > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json
{
  "agent": {
    "metrics_collection_interval": 60,
    "run_as_user": "root",
    "logfile": "/opt/aws/amazon-cloudwatch-agent/logs/amazon-cloudwatch-agent.log"
  },
  "metrics": {
    "metrics_collected": {
      "collectd": {
        "metrics_aggregation_interval": 60
      },
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
          {
            "file_path": "/opt/aws/amazon-cloudwatch-agent/logs/amazon-cloudwatch-agent.log",
            "log_group_name": "${DrupalSystemLogGroup}",
            "log_stream_name": "{instance_id}-/opt/aws/amazon-cloudwatch-agent/logs/amazon-cloudwatch-agent.log",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/dpkg.log",
            "log_group_name": "${DrupalSystemLogGroup}",
            "log_stream_name": "{instance_id}-/var/log/dpkg.log",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/apt/history.log",
            "log_group_name": "${DrupalSystemLogGroup}",
            "log_stream_name": "{instance_id}-/var/log/apt/history.log",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/cloud-init.log",
            "log_group_name": "${DrupalSystemLogGroup}",
            "log_stream_name": "{instance_id}-/var/log/cloud-init.log",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/cloud-init-output.log",
            "log_group_name": "${DrupalSystemLogGroup}",
            "log_stream_name": "{instance_id}-/var/log/cloud-init-output.log",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/auth.log",
            "log_group_name": "${DrupalSystemLogGroup}",
            "log_stream_name": "{instance_id}-/var/log/auth.log",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/syslog",
            "log_group_name": "${DrupalSystemLogGroup}",
            "log_stream_name": "{instance_id}-/var/log/syslog",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/amazon/ssm/amazon-ssm-agent.log",
            "log_group_name": "${DrupalSystemLogGroup}",
            "log_stream_name": "{instance_id}-/var/log/amazon/ssm/amazon-ssm-agent.log",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/amazon/ssm/errors.log",
            "log_group_name": "${DrupalSystemLogGroup}",
            "log_stream_name": "{instance_id}-/var/log/amazon/ssm/errors.log",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/apache2/access.log",
            "log_group_name": "${DrupalAccessLogGroup}",
            "log_stream_name": "{instance_id}-/var/log/apache2/access.log",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/apache2/error.log",
            "log_group_name": "${DrupalErrorLogGroup}",
            "log_stream_name": "{instance_id}-/var/log/apache2/error.log",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/apache2/access-ssl.log",
            "log_group_name": "${DrupalAccessLogGroup}",
            "log_stream_name": "{instance_id}-/var/log/apache2/access-ssl.log",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/apache2/error-ssl.log",
            "log_group_name": "${DrupalErrorLogGroup}",
            "log_stream_name": "{instance_id}-/var/log/apache2/error-ssl.log",
            "timezone": "UTC"
          }
        ]
      }
    },
    "log_stream_name": "{instance_id}"
  }
}
EOF
systemctl enable amazon-cloudwatch-agent
systemctl start amazon-cloudwatch-agent

# efs
mkdir /mnt/efs
mount -t efs "${AppEfs}":/ /mnt/efs
echo "${AppEfs}:/ /mnt/efs efs _netdev 0 0" >> /etc/fstab

# write application configuration values to env
DB_NAME=$(aws ssm get-parameter --name /oe/patterns/drupal/database-name --query Parameter.Value --output text)
DB_USER=$(aws ssm get-parameter --name /oe/patterns/drupal/database-user --query Parameter.Value --output text)
DB_PASSWORD=$(aws ssm get-parameter --name /oe/patterns/drupal/database-password --query Parameter.Value --output text)
HASH_SALT=$(aws ssm get-parameter --name /oe/patterns/drupal/hash-salt --query Parameter.Value --output text)
CONFIG_SYNC_DIR=$(aws ssm get-parameter --name /oe/patterns/drupal/config-sync-directory --query Parameter.Value --output text)

echo export OE_PATTERNS_DRUPAL_DATABASE_NAME=$DB_NAME >> /etc/profile.d/oe-patterns-drupal.sh
echo export OE_PATTERNS_DRUPAL_DATABASE_USER=$DB_USER >> /etc/profile.d/oe-patterns-drupal.sh
# TODO: currently using regular string ssm parameter for password to allow for user input use case
echo export OE_PATTERNS_DRUPAL_DATABASE_PASSWORD=$DB_PASSWORD >> /etc/profile.d/oe-patterns-drupal.sh
echo export OE_PATTERNS_DRUPAL_HASH_SALT=$HASH_SALT >> /etc/profile.d/oe-patterns-drupal.sh
echo export OE_PATTERNS_DRUPAL_CONFIG_SYNC_DIRECTORY=$CONFIG_SYNC_DIR >> /etc/profile.d/oe-patterns-drupal.sh

echo export OE_PATTERNS_DRUPAL_DATABASE_NAME=$DB_NAME >> /etc/apache2/envvars
echo export OE_PATTERNS_DRUPAL_DATABASE_USER=$DB_USER >> /etc/apache2/envvars
# TODO: currently using regular string ssm parameter for password to allow for user input use case
echo export OE_PATTERNS_DRUPAL_DATABASE_PASSWORD=$DB_PASSWORD >> /etc/apache2/envvars
echo export OE_PATTERNS_DRUPAL_HASH_SALT=$HASH_SALT >> /etc/apache2/envvars
echo export OE_PATTERNS_DRUPAL_CONFIG_SYNC_DIRECTORY=$CONFIG_SYNC_DIR >> /etc/apache2/envvars


mkdir -p /opt/oe/patterns/drupal
cat <<"EOF" > /opt/oe/patterns/drupal/settings.php
<?php

$settings['hash_salt'] = getenv('OE_PATTERNS_DRUPAL_HASH_SALT');

$databases['default']['default'] = array (
  'database' => getenv('OE_PATTERNS_DRUPAL_DATABASE_NAME'),
  'username' => getenv('OE_PATTERNS_DRUPAL_DATABASE_USER'),
  'password' => getenv('OE_PATTERNS_DRUPAL_DATABASE_PASSWORD'),
  'prefix' => '',
  'host' => '${DBCluster.Endpoint.Address}',
  'port' => '${DBCluster.Endpoint.Port}',
  'namespace' => 'Drupal\\Core\\Database\\Driver\\mysql',
  'driver' => 'mysql',
);
$settings['config_sync_directory'] = getenv('OE_PATTERNS_DRUPAL_CONFIG_SYNC_DIRECTORY');
EOF

# apache
openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
  -keyout /etc/ssl/private/apache-selfsigned.key \
  -out /etc/ssl/certs/apache-selfsigned.crt \
  -subj '/CN=localhost'
systemctl enable apache2 && systemctl start apache2

cfn-signal --exit-code $? --stack ${AWS::StackName} --resource AppAsg --region ${AWS::Region}
