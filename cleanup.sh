#!/usr/bin/env bash

BUCKETS=`aws s3 ls | awk '{print $3}'`

# PREFIX_TO_DELETE="tcat"
PREFIX_TO_DELETE="oe-patterns-drupal-${USER}"

for bucket in $BUCKETS; do
    if [[ $bucket == $PREFIX_TO_DELETE* ]]; then
        # echo $bucket
        aws s3 rb s3://$bucket --force
    fi
done
