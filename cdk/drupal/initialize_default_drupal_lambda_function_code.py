import os
import logging
import uuid

import boto3
import botocore
import cfnresponse

logger = logging.getLogger()
logger.setLevel("INFO")

cloudformation_client = boto3.client("cloudformation")
s3_client = boto3.client("s3")

def lambda_handler(event, context):
    logger.info("Initialize Default Drupal Lambda starting...")

    try:
        if (event["RequestType"] == "Create"):
            s3_client.copy_object(
                Bucket=os.environ["SourceArtifactBucket"],
                CopySource=os.environ["DefaultDrupalSourceArtifactBucket"] + "/" + os.environ["DefaultDrupalSourceArtifactObjectKey"],
                Key=os.environ["SourceArtifactObjectKey"]
            )
            logger.info("Drupal codebase copy complete.")

        cfnresponse.send(event, context, cfnresponse.SUCCESS, {})
        logger.info("CloudFormation success response sent.")

    except Exception as e:
        logger.error(e)
        cfnresponse.send(event, context, cfnresponse.FAILED, {})
        logger.error("CloudFormation failure response sent.")
        raise e
