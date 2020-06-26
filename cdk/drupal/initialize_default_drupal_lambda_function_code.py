import os
import logging
import uuid

import boto3
import botocore
from botocore.exceptions import ClientError
import cfnresponse

logger = logging.getLogger()
logger.setLevel("INFO")

cloudformation_client = boto3.client("cloudformation")
s3_client = boto3.client("s3")

def lambda_handler(event, context):
    logger.info("Initialize Default Drupal Lambda starting...")

    try:
        if (event["RequestType"] == "Create"):
            try:
                s3_client.head_object(
                    Bucket=os.environ["SourceArtifactBucket"],
                    Key=os.environ["SourceArtifactObjectKey"]
                )
            except ClientError as e:
                # perform the copy only if the object is not found
                # in this case that means a 404 ClientError from the HeadObject request
                if e.response["Error"]["Code"] == "404":
                    s3_client.copy_object(
                        Bucket=os.environ["SourceArtifactBucket"],
                        CopySource=os.environ["DefaultDrupalSourceArtifactBucket"] + "/" + os.environ["DefaultDrupalSourceArtifactObjectKey"],
                        Key=os.environ["SourceArtifactObjectKey"]
                    )
                    logger.info("Drupal codebase copy complete.")
                else:
                    logger.info("The artifact object already exists. Copy aborted.")

        cfnresponse.send(event, context, cfnresponse.SUCCESS, {})
        logger.info("CloudFormation success response sent.")

    except Exception as e:
        logger.error(e)
        cfnresponse.send(event, context, cfnresponse.FAILED, {})
        raise e
