import os
import logging


from datetime import date
from datetime import datetime
from datetime import timedelta

import boto3
import botocore
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel("INFO")

rds_client = boto3.client("rds")

def lambda_handler(event, context):
    logger.info("Lambda event starting...")

    today = date.today()
    date_str = today.strftime("%Y%m%d")
    date_today = int(today.strftime("%d"))
    
    logger.info("Today is day " + str(date_today) + " of the month")

    backup_type = "daily"
    if date_today == 1:
        backup_type = "monthly"

    snapshots = rds_client.describe_db_cluster_snapshots(
        DBClusterIdentifier=os.environ["DBClusterIdentifier"],
        SnapshotType="manual"
    )
    for snapshot in snapshots["DBClusterSnapshots"]:
        tags = rds_client.list_tags_for_resource(
            ResourceName=snapshot["DBClusterSnapshotArn"]
        )
        snapshot["TagList"] = tags["TagList"]
        
    # create db snapshot
    snapshot_already_created = False
    for snapshot in snapshots["DBClusterSnapshots"]:
        if has_drupal_lambda_backup_date_tag(snapshot, date_str):
            snapshot_already_created = True
            break
    if not snapshot_already_created:
        db_snapshot_identifier = "drupal-lambda-backup-" + os.environ["DBClusterIdentifier"] + "-" + date_str + "-" + backup_type
        logger.info("Creating DB snapshot: " + db_snapshot_identifier + "...")
        rds_client.create_db_cluster_snapshot(
            DBClusterSnapshotIdentifier=db_snapshot_identifier,
            DBClusterIdentifier=os.environ["DBClusterIdentifier"],
            Tags=[
                {
                    "Key": "drupal-lambda-backup-type",
                    "Value": backup_type
                },
                {
                    "Key": "drupal-lambda-backup-date",
                    "Value": date_str
                },
                {
                    "Key": "stack-name",
                    "Value": os.environ["StackName"]
                }
            ]
        )
    else:
        logger.info("Found an existing snapshot for today, skipping creation")

    # delete daily backups older than one month
    for snapshot in snapshots["DBClusterSnapshots"]:
        if (has_stack_name_tag(snapshot) and has_daily_drupal_lambda_backup_type_tag(snapshot)):
            db_cluster_snapshot_identifier = snapshot["DBClusterSnapshotIdentifier"]
            if "SnapshotCreateTime" in snapshot:
                snapshot_create_time = snapshot["SnapshotCreateTime"].replace(tzinfo=None)
                if snapshot_create_time < datetime.now() - timedelta(weeks=4):
                    logger.info("Deleting snapshot " + db_cluster_snapshot_identifier + "...")
                    rds_client.delete_db_cluster_snapshot(
                        DBClusterSnapshotIdentifier=db_cluster_snapshot_identifier
                    )

def has_stack_name_tag(snapshot_with_tags):
    for tag in snapshot_with_tags["TagList"]:
        if tag["Key"] == "stack-name" and tag["Value"] == os.environ["StackName"]:
            return True
    return False

def has_daily_drupal_lambda_backup_type_tag(snapshot_with_tags):
    for tag in snapshot_with_tags["TagList"]:
        if tag["Key"] == "drupal-lambda-backup-type" and tag["Value"] == "daily":
            return True
    return False

def has_drupal_lambda_backup_date_tag(snapshot_with_tags, date_str):
    for tag in snapshot_with_tags["TagList"]:
        if tag["Key"] == "drupal-lambda-backup-date" and tag["Value"] == date_str:
            return True
    return False
