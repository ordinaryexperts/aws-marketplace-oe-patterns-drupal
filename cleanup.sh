#!/usr/bin/env bash

TYPE="${1:-all}"
PREFIX="${2:-user}"

if [[ $PREFIX == "tcat" ]]; then
    PREFIX_TO_DELETE="tcat"
else
    PREFIX_TO_DELETE="oe-patterns-drupal-${USER}"
fi

if [[ $TYPE == "all" || $TYPE == "buckets" ]]; then
    echo "Removing $PREFIX_TO_DELETE buckets..."
    BUCKETS=`aws s3 ls | awk '{print $3}'`
    for bucket in $BUCKETS; do
        if [[ $bucket == $PREFIX_TO_DELETE* ]]; then
            # echo $bucket
            aws s3 rb s3://$bucket --force
        fi
    done
    echo "done."
fi

if [[ $TYPE == "all" || $TYPE == "snapshots" ]]; then
    echo "Removing $PREFIX_TO_DELETE snapshots..."
    SNAPSHOTS=`aws rds describe-db-cluster-snapshots | jq -r '.DBClusterSnapshots[].DBClusterSnapshotIdentifier'`
    for snapshot in $SNAPSHOTS; do
        if [[ $snapshot == $PREFIX_TO_DELETE* ]]; then
            echo $snapshot
            aws rds delete-db-cluster-snapshot --db-cluster-snapshot-identifier $snapshot
        fi
    done
    echo "done."
fi

if [[ $TYPE == "all" || $TYPE == "logs" ]]; then
    echo "Removing $PREFIX_TO_DELETE log groups..."
    LOG_GROUPS=`aws logs describe-log-groups | jq -r '.logGroups[].logGroupName'`
    for log_group in $LOG_GROUPS; do
        if [[ $log_group == $PREFIX_TO_DELETE* ]]; then
            echo $log_group
            aws logs delete-log-group --log-group-name $log_group
        fi
        if [[ $PREFIX_TO_DELETE == "tcat" ]]; then
            if [[ $log_group == tCaT* ]]; then
                echo $log_group
                aws logs delete-log-group --log-group-name $log_group
            fi
        fi
        if [[ $log_group == /aws/rds/cluster/$PREFIX_TO_DELETE* ]]; then
            echo $log_group
            aws logs delete-log-group --log-group-name $log_group
        fi
    done
    echo "done."
fi
