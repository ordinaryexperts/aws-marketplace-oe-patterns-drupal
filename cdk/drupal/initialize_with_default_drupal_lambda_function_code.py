import os
import logging

import boto3
import botocore

logger = logging.getLogger()
logger.setLevel("INFO")

s3_client = boto3.client("s3")

def lambda_handler(event, context):
    logger.info("Initialize Default Drupal Lambda starting...")

    s3_client.copy_object(
        Bucket=os.environ["SourceArtifactBucket"],
        CopySource=os.environ["DefaultDrupalSourceArtifactBucket"] + "/" + os.environ["DefaultDrupalSourceArtifactObjectKey"],
        Key=os.environ["SourceArtifactObjectKey"]
    )
