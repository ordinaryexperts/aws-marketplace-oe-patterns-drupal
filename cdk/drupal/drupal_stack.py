import json
import os
import subprocess
import yaml
from aws_cdk import (
    Arn,
    ArnComponents,
    Aws,
    aws_cloudformation,
    aws_cloudfront,
    aws_codebuild,
    aws_codedeploy,
    aws_codepipeline,
    aws_ec2,
    aws_elasticache,
    aws_iam,
    aws_lambda,
    aws_logs,
    aws_rds,
    aws_s3,
    aws_secretsmanager,
    aws_sns,
    CfnCondition,
    CfnDeletionPolicy,
    CfnMapping,
    CfnOutput,
    CfnParameter,
    CfnResource,
    CfnRule,
    CfnRuleAssertion,
    Fn,
    Stack,
    Tags,
    Token
)
from constructs import Construct

from oe_patterns_cdk_common.alb import Alb
from oe_patterns_cdk_common.asg import Asg
from oe_patterns_cdk_common.dns import Dns
from oe_patterns_cdk_common.efs import Efs
from oe_patterns_cdk_common.vpc import Vpc

DEFAULT_DRUPAL_SOURCE_URL="https://ordinary-experts-aws-marketplace-drupal-pattern-artifacts.s3.amazonaws.com/aws-marketplace-oe-patterns-drupal-example-site/refs/heads/feature/upgrade-drupal.zip"

TWO_YEARS_IN_DAYS=731
if 'TEMPLATE_VERSION' in os.environ:
    template_version = os.environ['TEMPLATE_VERSION']
else:
    try:
        template_version = subprocess.check_output(["git", "describe"]).strip().decode('ascii')
    except:
        template_version = "CICD"

# When making a new development AMI:
# 1) $ ave oe-patterns-dev make ami-ec2-build
# 2) $ ave oe-patterns-dev make AMI_ID=ami-fromstep1 ami-ec2-copy
# 3) Copy the code that copy-image generates below

AMI_ID="ami-0962921aa6e19218f"
AMI_NAME="ordinary-experts-patterns-drupal--20220822-0556"
generated_ami_ids = {
    "us-east-1": "ami-0962921aa6e19218f"
}

# Sanity check: if this fails then make copy-image needs to be run...
assert AMI_ID == generated_ami_ids["us-east-1"]

class DrupalStack(Stack):

    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        #
        # INITIALIZATION
        #

        current_directory = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
        allowed_values = yaml.load(
            open(os.path.join(current_directory, "allowed_values.yaml")),
            Loader=yaml.SafeLoader
        )
        ami_mapping={
            "AMI": {
                "AMI": AMI_NAME
            }
        }
        for region in generated_ami_ids.keys():
            ami_mapping[region] = { "AMI": generated_ami_ids[region] }
        aws_ami_region_map = CfnMapping(
            self,
            "AWSAMIRegionMap",
            mapping=ami_mapping
        )

        # utility function to parse the unique id from the stack id for
        # shorter resource names using cloudformation functions
        def append_stack_uuid(name):
            return Fn.join("-", [
                name,
                Fn.select(2, Fn.split("/", Aws.STACK_ID))
            ])

        #
        # PARAMETERS
        #

        cloudfront_aliases_param = CfnParameter(
            self,
            "CloudFrontAliases",
            default="",
            description="Optional: A list of hostname aliases registered with the CloudFront distribution. If a certificate is supplied, each hostname must validate against the certificate.",
            type="CommaDelimitedList"
        )
        cloudfront_certificate_arn_param = CfnParameter(
            self,
            "CloudFrontCertificateArn",
            default="",
            description="Optional: The ARN from AWS Certificate Manager for the SSL cert used in CloudFront CDN. Must be in us-east-1 region."
        )
        cloudfront_enable_param = CfnParameter(
            self,
            "CloudFrontEnable",
            allowed_values=[ "true", "false" ],
            default="false",
            description="Required: Enable CloudFront CDN support."
        )
        cloudfront_price_class_param = CfnParameter(
            self,
            "CloudFrontPriceClass",
            # possible to use a map to make the values more human readable
            allowed_values = [
                "PriceClass_All",
                "PriceClass_200",
                "PriceClass_100"
            ],
            default="PriceClass_All",
            description="Required: Price class to use for CloudFront CDN (only applies when CloudFront enabled)."
        )
        db_instance_class_param = CfnParameter(
            self,
            "DbInstanceClass",
            allowed_values=allowed_values["allowed_db_instance_types"],
            default="db.r5.large",
            description="Required: The class profile for memory and compute capacity for the database instance."
        )
        db_snapshot_identifier_param = CfnParameter(
            self,
            "DbSnapshotIdentifier",
            default="",
            description="Optional: RDS snapshot ARN from which to restore. If specified, manually edit the secret values to specify the snapshot credentials for the application. WARNING: Changing this value will re-provision the database."
        )
        elasticache_cluster_cache_node_type_param = CfnParameter(
            self,
            "ElastiCacheClusterCacheNodeType",
            allowed_values=allowed_values["allowed_cache_instance_types"],
            default="cache.t3.micro",
            description="Required: Instance type for the memcached cluster nodes (only applies when ElastiCache enabled)."
        )
        elasticache_cluster_engine_version_param = CfnParameter(
            self,
            "ElastiCacheClusterEngineVersion",
            allowed_values=[ "1.4.14", "1.4.24", "1.4.33", "1.4.34", "1.4.5", "1.5.10", "1.5.16" ],
            default="1.5.16",
            description="Required: The memcached version of the cache cluster (only applies when ElastiCache enabled)."
        )
        elasticache_cluster_num_cache_nodes_param = CfnParameter(
            self,
            "ElastiCacheClusterNumCacheNodes",
            default=2,
            description="Required: The number of cache nodes in the memcached cluster (only applies ElastiCache enabled).",
            min_value=1,
            max_value=20,
            type="Number"
        )
        elasticache_enable_param = CfnParameter(
            self,
            "ElastiCacheEnable",
            allowed_values=[ "true", "false" ],
            default="false",
            description="Required: Whether to provision ElastiCache memcached cluster."
        )
        initialize_default_drupal_param = CfnParameter(
            self,
            "InitializeDefaultDrupal",
            allowed_values=[ "true", "false" ],
            default="true",
            description="Optional: Trigger the first deployment with a copy of an initial default codebase from Ordinary Experts using Drupal 9 and some common modules taking advantage of the stack capabilities."
        )
        initialize_default_drupal_condition = CfnCondition(
            self,
            "InitializeDefaultDrupalCondition",
            expression=Fn.condition_equals(initialize_default_drupal_param.value, "true")
        )
        notification_email_param = CfnParameter(
            self,
            "NotificationEmail",
            default="",
            description="Optional: Specify an email address to get emails about deploys and other system events."
        )
        pipeline_artifact_bucket_name_param = CfnParameter(
            self,
            "PipelineArtifactBucketName",
            default="",
            description="Optional: Specify a bucket name for the CodePipeline pipeline to use. The bucket must be in this same AWS account. This can be handy when re-creating this template many times."
        )
        secret_arn_param = CfnParameter(
            self,
            "SecretArn",
            default="",
            description="Optional: SecretsManager secret ARN used to store database credentials and other configuration. If not specified, a secret will be created."
        )
        source_artifact_bucket_name_param = CfnParameter(
            self,
            "SourceArtifactBucketName",
            default="",
            description="Optional: Specify a S3 Bucket name which will contain the build artifacts for the application. If not specified, a bucket will be created."
        )
        source_artifact_object_key_param = CfnParameter(
            self,
            "SourceArtifactObjectKey",
            default="drupal.zip",
            description="Required: AWS S3 Object key (path) for the build artifact for the application.  Updates to this object will trigger a deployment."
        )

        #
        # CONDITIONS
        #

        cloudfront_aliases_exist_condition = CfnCondition(
            self,
            "CloudFrontAliasesExist",
            expression=Fn.condition_not(
                Fn.condition_equals(Fn.select(0, cloudfront_aliases_param.value_as_list), "")
            )
        )
        cloudfront_certificate_arn_exists_condition = CfnCondition(
            self,
            "CloudFrontCertificateArnExists",
            expression=Fn.condition_not(Fn.condition_equals(cloudfront_certificate_arn_param.value, ""))
        )
        cloudfront_enable_condition = CfnCondition(
            self,
            "CloudFrontEnableCondition",
            expression=Fn.condition_equals(cloudfront_enable_param.value, "true")
        )
        db_snapshot_identifier_exists_condition = CfnCondition(
            self,
            "DbSnapshotIdentifierExistsCondition",
            expression=Fn.condition_not(Fn.condition_equals(db_snapshot_identifier_param.value, ""))
        )
        elasticache_enable_condition = CfnCondition(
            self,
            "ElastiCacheEnableCondition",
            expression=Fn.condition_equals(elasticache_enable_param.value, "true")
        )
        notification_email_exists_condition = CfnCondition(
            self,
            "NotificationEmailExists",
            expression=Fn.condition_not(Fn.condition_equals(notification_email_param.value, ""))
        )
        pipeline_artifact_bucket_name_not_exists_condition = CfnCondition(
            self,
            "PipelineArtifactBucketNameNotExists",
            expression=Fn.condition_equals(pipeline_artifact_bucket_name_param.value, "")
        )
        pipeline_artifact_bucket_name_exists_condition = CfnCondition(
            self,
            "PipelineArtifactBucketNameExists",
            expression=Fn.condition_not(Fn.condition_equals(pipeline_artifact_bucket_name_param.value, ""))
        )
        secret_arn_exists_condition = CfnCondition(
            self,
            "SecretArnExistsCondition",
            expression=Fn.condition_not(Fn.condition_equals(secret_arn_param.value, ""))
        )
        secret_arn_not_exists_condition = CfnCondition(
            self,
            "SecretArnNotExistsCondition",
            expression=Fn.condition_equals(secret_arn_param.value, "")
        )
        source_artifact_bucket_name_exists_condition = CfnCondition(
            self,
            "SourceArtifactBucketNameExists",
            expression=Fn.condition_not(Fn.condition_equals(source_artifact_bucket_name_param.value, ""))
        )
        source_artifact_bucket_name_not_exists_condition = CfnCondition(
            self,
            "SourceArtifactBucketNameNotExists",
            expression=Fn.condition_equals(source_artifact_bucket_name_param.value, "")
        )

        #
        # RULES
        #

        cloudfront_aliases_certificate_rule = CfnRule(
            self,
            "CloudFrontAliasesAndCertificateRequiredRule",
            assertions=[
                CfnRuleAssertion(
                    assert_=Fn.condition_not(
                        Fn.condition_equals(cloudfront_certificate_arn_param.value_as_string, "")
                    ),
                    assert_description="When providing a set of aliases for CloudFront, you must also supply a trusted CloudFrontCertificateArn parameter which validates your authorization to use those domain names"
                )
            ],
            rule_condition=Fn.condition_not(
                Fn.condition_each_member_equals(cloudfront_aliases_param.value_as_list, "")
            )
        )
        db_snapshot_secret_rule = CfnRule(
            self,
            "DbSnapshotIdentifierAndSecretRequiredRule",
            assertions=[
                CfnRuleAssertion(
                    assert_=Fn.condition_not(Fn.condition_equals(secret_arn_param.value_as_string, "")),
                    assert_description="When restoring the database from a snapshot, a secret ARN must also be supplied, prepopulated with username and password key-value pairs which correspond to the snapshot image"
                )
            ],
            rule_condition=Fn.condition_not(
                Fn.condition_equals(db_snapshot_identifier_param.value_as_string, "")
            )
        )

        #
        # RESOURCES
        #

        pipeline_artifact_bucket = aws_s3.CfnBucket(
            self,
            "PipelineArtifactBucket",
            access_control="Private",
            bucket_encryption=aws_s3.CfnBucket.BucketEncryptionProperty(
                server_side_encryption_configuration=[
                    aws_s3.CfnBucket.ServerSideEncryptionRuleProperty(
                        server_side_encryption_by_default=aws_s3.CfnBucket.ServerSideEncryptionByDefaultProperty(
                            sse_algorithm="AES256"
                        )
                    )
                ]
            ),
            public_access_block_configuration=aws_s3.BlockPublicAccess.BLOCK_ALL
        )
        pipeline_artifact_bucket.cfn_options.condition=pipeline_artifact_bucket_name_not_exists_condition
        pipeline_artifact_bucket.cfn_options.deletion_policy = CfnDeletionPolicy.RETAIN
        pipeline_artifact_bucket.cfn_options.update_replace_policy = CfnDeletionPolicy.RETAIN
        pipeline_artifact_bucket_arn = Arn.format(
            components=ArnComponents(
                account="",
                region="",
                resource=Token.as_string(
                    Fn.condition_if(
                        pipeline_artifact_bucket_name_exists_condition.logical_id,
                        pipeline_artifact_bucket_name_param.value_as_string,
                        pipeline_artifact_bucket.ref
                    )
                ),
                resource_name="*",
                service="s3"
            ),
            stack=self
        )
        source_artifact_bucket = aws_s3.CfnBucket(
            self,
            "SourceArtifactBucket",
            access_control="Private",
            bucket_encryption=aws_s3.CfnBucket.BucketEncryptionProperty(
                server_side_encryption_configuration=[
                    aws_s3.CfnBucket.ServerSideEncryptionRuleProperty(
                        server_side_encryption_by_default=aws_s3.CfnBucket.ServerSideEncryptionByDefaultProperty(
                            sse_algorithm="AES256"
                        )
                    )
                ]
            ),
            public_access_block_configuration=aws_s3.BlockPublicAccess.BLOCK_ALL,
            versioning_configuration=aws_s3.CfnBucket.VersioningConfigurationProperty(
                status="Enabled"
            )
        )
        source_artifact_bucket.cfn_options.condition = source_artifact_bucket_name_not_exists_condition
        source_artifact_bucket.cfn_options.deletion_policy = CfnDeletionPolicy.RETAIN
        source_artifact_bucket.cfn_options.update_replace_policy = CfnDeletionPolicy.RETAIN
        source_artifact_bucket_name = Token.as_string(
            Fn.condition_if(
                source_artifact_bucket_name_exists_condition.logical_id,
                source_artifact_bucket_name_param.value_as_string,
                source_artifact_bucket.ref
            )
        )
        source_artifact_bucket_arn = Arn.format(
            components=ArnComponents(
                account="",
                region="",
                resource=source_artifact_bucket_name,
                service="s3"
            ),
            stack=self
        )
        source_artifact_object_key_arn = Arn.format(
            components=ArnComponents(
                account="",
                region="",
                resource=source_artifact_bucket_name,
                resource_name=source_artifact_object_key_param.value_as_string,
                service="s3"
            ),
            stack=self
        )

        # vpc
        vpc = Vpc(
            self,
            "Vpc"
        )

        db_sg = aws_ec2.CfnSecurityGroup(
            self,
            "DbSg",
            group_description="Database SG",
            vpc_id=vpc.id()
        )
        db_subnet_group = aws_rds.CfnDBSubnetGroup(
            self,
            "DbSubnetGroup",
            db_subnet_group_description="MySQL Aurora DB Subnet Group",
            subnet_ids=vpc.private_subnet_ids()
        )
        db_cluster_parameter_group = aws_rds.CfnDBClusterParameterGroup(
            self,
            "DbClusterParameterGroup",
            description="test",
            family="aurora-mysql5.7",
            parameters={
                "character_set_client": "utf8",
                "character_set_connection": "utf8",
                "character_set_database": "utf8",
                "character_set_filesystem": "utf8",
                "character_set_results": "utf8",
                "character_set_server": "utf8",
                "collation_connection": "utf8_general_ci",
                "collation_server": "utf8_general_ci"
            }
        )
        db_parameter_group = aws_rds.CfnDBParameterGroup(
            self,
            "DbParameterGroup",
            description="Aurora DB Instance Parameter Group",
            family="aurora-mysql5.7",
            parameters={
                "general_log": "1",
                "log_output": "FILE",
                "log_queries_not_using_indexes": "1",
                "long_query_time": "10",
                "slow_query_log": "1"
            }
        )
        secret = aws_secretsmanager.CfnSecret(
            self,
            "Secret",
            generate_secret_string=aws_secretsmanager.CfnSecret.GenerateSecretStringProperty(
                exclude_characters="\"@/\\\"'$,[]*?{}~\#%<>|^",
                exclude_punctuation=True,
                generate_string_key="password",
                secret_string_template=json.dumps({"username":"dbadmin"})
            ),
            name="{}/drupal/secret".format(Aws.STACK_NAME)
        )
        secret.cfn_options.condition = secret_arn_not_exists_condition

        db_cluster = aws_rds.CfnDBCluster(
            self,
            "DbCluster",
            db_cluster_parameter_group_name=db_cluster_parameter_group.ref,
            db_subnet_group_name=db_subnet_group.ref,
            engine="aurora-mysql",
            engine_mode="provisioned",
            engine_version="5.7.mysql_aurora.2.08.0",
            master_username=Token.as_string(
                Fn.condition_if(
                    db_snapshot_identifier_exists_condition.logical_id,
                    Aws.NO_VALUE,
                    Fn.condition_if(
                        secret_arn_exists_condition.logical_id,
                        Fn.sub("{{resolve:secretsmanager:${SecretArn}:SecretString:username}}"),
                        Fn.sub("{{resolve:secretsmanager:${Secret}:SecretString:username}}")
                    ),
                )
            ),
            master_user_password=Token.as_string(
                Fn.condition_if(
                    db_snapshot_identifier_exists_condition.logical_id,
                    Aws.NO_VALUE,
                    Fn.condition_if(
                        secret_arn_exists_condition.logical_id,
                        Fn.sub("{{resolve:secretsmanager:${SecretArn}:SecretString:password}}"),
                        Fn.sub("{{resolve:secretsmanager:${Secret}:SecretString:password}}"),
                    ),
                )
            ),
            snapshot_identifier=Token.as_string(
                Fn.condition_if(
                    db_snapshot_identifier_exists_condition.logical_id,
                    db_snapshot_identifier_param.value_as_string,
                    Aws.NO_VALUE
                )
            ),
            storage_encrypted=True,
            vpc_security_group_ids=[ db_sg.ref ]
        )
        db_primary_instance = aws_rds.CfnDBInstance(
            self,
            "DbPrimaryInstance",
            db_cluster_identifier=db_cluster.ref,
            db_instance_class=db_instance_class_param.value_as_string,
            db_instance_identifier=Token.as_string(
                Fn.condition_if(
                    db_snapshot_identifier_exists_condition.logical_id,
                    Aws.NO_VALUE,
                    append_stack_uuid("drupal")
                )
            ),
            db_parameter_group_name=db_parameter_group.ref,
            db_subnet_group_name=db_subnet_group.ref,
            engine="aurora-mysql",
            publicly_accessible=False
        )

        # notifications
        notification_topic = aws_sns.CfnTopic(
            self,
            "NotificationTopic",
            topic_name=append_stack_uuid(f"{Aws.STACK_NAME}-notifications")
        )
        notification_subscription = aws_sns.CfnSubscription(
            self,
            "NotificationSubscription",
            protocol="email",
            topic_arn=notification_topic.ref,
            endpoint=notification_email_param.value_as_string
        )
        notification_subscription.cfn_options.condition = notification_email_exists_condition
        iam_notification_publish_policy =aws_iam.PolicyDocument(
            statements=[
                aws_iam.PolicyStatement(
                    effect=aws_iam.Effect.ALLOW,
                    actions=[ "sns:Publish" ],
                    resources=[ notification_topic.ref ]
                )
            ]
        )

        # elasticache
        elasticache_sg = aws_ec2.CfnSecurityGroup(
            self,
            "ElastiCacheSg",
            group_description="App SG",
            vpc_id=vpc.id()
        )
        elasticache_sg.cfn_options.condition = elasticache_enable_condition
        elasticache_subnet_group = CfnResource(
            self,
            "ElastiCacheSubnetGroup",
            type="AWS::ElastiCache::SubnetGroup",
            properties={
                "Description": "ElastiCache subnet group.",
                "SubnetIds":  vpc.private_subnet_ids()
            }
        )
        elasticache_subnet_group.cfn_options.condition = elasticache_enable_condition
        elasticache_cluster = aws_elasticache.CfnCacheCluster(
            self,
            "ElastiCacheCluster",
            az_mode="cross-az",
            cache_node_type=elasticache_cluster_cache_node_type_param.value_as_string,
            cache_subnet_group_name=elasticache_subnet_group.ref,
            engine="memcached",
            engine_version=elasticache_cluster_engine_version_param.value_as_string,
            num_cache_nodes=elasticache_cluster_num_cache_nodes_param.value_as_number,
            vpc_security_group_ids=[ elasticache_sg.ref ]
        )
        Tags.of(elasticache_cluster).add("oe:patterns:drupal:stack", Aws.STACK_NAME)
        elasticache_cluster.cfn_options.condition = elasticache_enable_condition

        # autoscaling
        with open("drupal/app_launch_config_user_data.sh") as f:
            app_launch_config_user_data = f.read()
        asg = Asg(
            self,
            "Asg",
            secret_arn = Token.as_string(
                Fn.condition_if(
                    secret_arn_exists_condition.logical_id,
                    secret_arn_param.value_as_string,
                    secret.ref
                )
            ),
            deployment_rolling_update = True,
            pipeline_bucket_arn = pipeline_artifact_bucket_arn,
            user_data_contents=app_launch_config_user_data,
            user_data_variables={
                "DrupalSalt": Fn.base64(Aws.STACK_ID),
                "ElastiCacheClusterHost": Token.as_string(
                    Fn.condition_if(
                        elasticache_enable_condition.logical_id,
                        elasticache_cluster.attr_configuration_endpoint_address,
                        ""
                    )
                ),
                "ElastiCacheClusterPort": Token.as_string(
                    Fn.condition_if(
                        elasticache_enable_condition.logical_id,
                        elasticache_cluster.attr_configuration_endpoint_port,
                        ""
                    )
                ),
                "HostnameParameterName": Aws.STACK_NAME + "-hostname",
                "SecretArn": Token.as_string(
                    Fn.condition_if(
                        secret_arn_exists_condition.logical_id,
                        secret_arn_param.value_as_string,
                        secret.ref
                    )
                )
            },
            vpc=vpc
        )

        # alb
        alb = Alb(self, "Alb", asg=asg, vpc=vpc)
        asg.asg.target_group_arns = [ alb.target_group.ref ]
        dns = Dns(self, "Dns", alb=alb)

        # cloudfront
        cloudfront_distribution = aws_cloudfront.CfnDistribution(
            self,
            "CloudFrontDistribution",
            distribution_config=aws_cloudfront.CfnDistribution.DistributionConfigProperty(
                aliases=Token.as_list(
                    Fn.condition_if(
                        cloudfront_aliases_exist_condition.logical_id,
                        cloudfront_aliases_param.value_as_list,
                        Aws.NO_VALUE
                    )
                ),
                comment=Aws.STACK_NAME,
                default_cache_behavior=aws_cloudfront.CfnDistribution.DefaultCacheBehaviorProperty(
                    allowed_methods=[
                        "DELETE",
                        "GET",
                        "HEAD",
                        "OPTIONS",
                        "PATCH",
                        "POST",
                        "PUT"
                    ],
                    compress=True,
                    default_ttl=86400,
                    forwarded_values=aws_cloudfront.CfnDistribution.ForwardedValuesProperty(
                        cookies=aws_cloudfront.CfnDistribution.CookiesProperty(
                            forward="whitelist",
                            whitelisted_names=[ "SESS*" ]
                        ),
                        headers=[
                            "CloudFront-Forwarded-Proto",
                            "Host",
                            "Origin"
                        ],
                        query_string=True
                    ),
                    min_ttl=0,
                    max_ttl=31536000,
                    target_origin_id="alb",
                    # when alb certificate is supplied, we automatically redirect http traffic to https.
                    # using that as a best-practice pattern, we redirect all traffic at cloudfront as well,
                    # covered either by the default AWS cloudfront cert when no aliases are supplied, or by the
                    # cert of the CloudFrontCertificateArn parameter.
                    viewer_protocol_policy="redirect-to-https"
                ),
                enabled=True,
                origins=[ aws_cloudfront.CfnDistribution.OriginProperty(
                    domain_name=alb.alb.attr_dns_name,
                    id="alb",
                    custom_origin_config=aws_cloudfront.CfnDistribution.CustomOriginConfigProperty(
                        origin_protocol_policy="https-only",
                        origin_ssl_protocols=[ "TLSv1.1", "TLSv1.2" ]
                    )
                )],
                price_class=cloudfront_price_class_param.value_as_string,
                viewer_certificate=aws_cloudfront.CfnDistribution.ViewerCertificateProperty(
                    acm_certificate_arn=Token.as_string(
                        Fn.condition_if(
                            cloudfront_certificate_arn_exists_condition.logical_id,
                            cloudfront_certificate_arn_param.value_as_string,
                            Aws.NO_VALUE
                        )
                    ),
                    cloud_front_default_certificate=Fn.condition_if(
                        cloudfront_certificate_arn_exists_condition.logical_id,
                        Aws.NO_VALUE,
                        True
                    ),
                    minimum_protocol_version=Token.as_string(
                        Fn.condition_if(
                            cloudfront_certificate_arn_exists_condition.logical_id,
                            "TLSv1.2_2018",
                            Aws.NO_VALUE
                        )
                    ),
                    ssl_support_method=Token.as_string(
                        Fn.condition_if(
                            cloudfront_certificate_arn_exists_condition.logical_id,
                            "sni-only",
                            Aws.NO_VALUE
                        )
                    )
                )
            )
        )
        cloudfront_distribution_arn = Arn.format(
            components=ArnComponents(
                account=Aws.ACCOUNT_ID,
                region="",
                resource="distribution",
                resource_name=cloudfront_distribution.ref,
                service="cloudfront"
            ),
            stack=self
        )
        cloudfront_distribution.cfn_options.condition = cloudfront_enable_condition
        cloudfront_invalidation_lambda_function_role = aws_iam.CfnRole(
            self,
            "CloudFrontInvalidationLambdaFunctionRole",
            assume_role_policy_document=aws_iam.PolicyDocument(
                statements=[
                    aws_iam.PolicyStatement(
                        effect=aws_iam.Effect.ALLOW,
                        actions=[ "sts:AssumeRole" ],
                        principals=[ aws_iam.ServicePrincipal("lambda.amazonaws.com") ]
                    )
                ]
            ),
            managed_policy_arns=[
                "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
            ],
            policies=[
                aws_iam.CfnRole.PolicyProperty(
                    policy_document=aws_iam.PolicyDocument(
                        statements=[
                            aws_iam.PolicyStatement(
                                effect=aws_iam.Effect.ALLOW,
                                actions=[ "cloudfront:CreateInvalidation" ],
                                resources=[ cloudfront_distribution_arn ]
                            )
                        ]
                    ),
                    policy_name="CloudFrontInvalidation"
                ),
                aws_iam.CfnRole.PolicyProperty(
                    policy_document=aws_iam.PolicyDocument(
                        statements=[
                            aws_iam.PolicyStatement(
                                effect=aws_iam.Effect.ALLOW,
                                actions=[
                                    "codepipeline:PutJobSuccessResult",
                                    "codepipeline:PutJobFailureResult"
                                ],
                                resources=[ "*" ]
                            )
                        ]
                    ),
                    policy_name="CodePipelineResult"
                ),
                aws_iam.CfnRole.PolicyProperty(
                    policy_document=iam_notification_publish_policy,
                    policy_name="SnsPublishToNotificationTopic"
                )
            ]
        )
        cloudfront_invalidation_lambda_function_role.cfn_options.condition = cloudfront_enable_condition
        with open("drupal/cloudfront_invalidation_lambda_function_code.py") as f:
            cloudfront_invalidation_lambda_function_code = f.read()
        cloudfront_invalidation_lambda_function = aws_lambda.CfnFunction(
            self,
            "CloudFrontInvalidationLambdaFunction",
            code=aws_lambda.CfnFunction.CodeProperty(
                zip_file=cloudfront_invalidation_lambda_function_code
            ),
            dead_letter_config=aws_lambda.CfnFunction.DeadLetterConfigProperty(
                target_arn=notification_topic.ref
            ),
            environment=aws_lambda.CfnFunction.EnvironmentProperty(
                variables={
                    "CloudFrontDistributionId": cloudfront_distribution.ref,
                }
            ),
            handler="index.lambda_handler",
            role=cloudfront_invalidation_lambda_function_role.attr_arn,
            runtime="python3.7"
        )
        cloudfront_invalidation_lambda_function.cfn_options.condition = cloudfront_enable_condition

        # efs
        efs = Efs(self, "Efs", app_sg=asg.sg, vpc=vpc)

        elasticache_sg_ingress = aws_ec2.CfnSecurityGroupIngress(
            self,
            "ElasticacheSgIngress",
            from_port=11211,
            group_id=elasticache_sg.ref,
            ip_protocol="tcp",
            source_security_group_id=asg.sg.ref,
            to_port=11211
        )
        elasticache_sg_ingress.cfn_options.condition = elasticache_enable_condition
        db_sg_ingress = aws_ec2.CfnSecurityGroupIngress(
            self,
            "DbSgIngress",
            from_port=3306,
            group_id=db_sg.ref,
            ip_protocol="tcp",
            source_security_group_id=asg.sg.ref,
            to_port=3306
        )

        # codebuild
        codebuild_transform_service_role = aws_iam.CfnRole(
            self,
            "CodeBuildTransformServiceRole",
            assume_role_policy_document=aws_iam.PolicyDocument(
                statements=[
                    aws_iam.PolicyStatement(
                        effect=aws_iam.Effect.ALLOW,
                        actions=[ "sts:AssumeRole" ],
                        principals=[ aws_iam.ServicePrincipal("codebuild.amazonaws.com") ]
                    )
                ]
            ),
            policies=[
                aws_iam.CfnRole.PolicyProperty(
                    policy_document=aws_iam.PolicyDocument(
                        statements=[
                            aws_iam.PolicyStatement(
                                effect=aws_iam.Effect.ALLOW,
                                actions=[
                                    "logs:CreateLogGroup",
                                    "logs:CreateLogStream",
                                    "logs:PutLogEvents"
                                ],
                                resources=[ "*" ]
                            ),
                            aws_iam.PolicyStatement(
                                effect=aws_iam.Effect.ALLOW,
                                actions=[
                                    "s3:GetObject",
                                    "s3:PutObject"
                                ],
                                resources=[ pipeline_artifact_bucket_arn ]
                            )
                        ]
                    ),
                    policy_name="TransformRolePermssions"
                )
            ]
        )
        codebuild_transform_service_role_arn = Arn.format(
            components=ArnComponents(
                account=Aws.ACCOUNT_ID,
                region="",
                resource="role",
                resource_name=codebuild_transform_service_role.ref,
                service="iam"
            ),
            stack=self
        )
        with open("drupal/codebuild_transform_project_buildspec.yml") as f:
            codebuild_transform_project_buildspec = f.read()
        codebuild_transform_project = aws_codebuild.CfnProject(
            self,
            "CodeBuildTransformProject",
            artifacts=aws_codebuild.CfnProject.ArtifactsProperty(
                type="CODEPIPELINE",
            ),
            environment=aws_codebuild.CfnProject.EnvironmentProperty(
                compute_type="BUILD_GENERAL1_SMALL",
                environment_variables=[
                    aws_codebuild.CfnProject.EnvironmentVariableProperty(
                        name="AUTO_SCALING_GROUP_NAME",
                        value=asg.asg.ref,
                    )
                ],
                image="aws/codebuild/standard:4.0",
                type="LINUX_CONTAINER"
            ),
            name="{}-transform".format(Aws.STACK_NAME),
            service_role=codebuild_transform_service_role_arn,
            source=aws_codebuild.CfnProject.SourceProperty(
                build_spec=codebuild_transform_project_buildspec,
                type="CODEPIPELINE"
            )
        )

        # codepipeline
        # TODO: Tighten role / use managed roles?
        codepipeline_role = aws_iam.CfnRole(
            self,
            "PipelineRole",
            assume_role_policy_document=aws_iam.PolicyDocument(
                statements=[
                    aws_iam.PolicyStatement(
                        effect=aws_iam.Effect.ALLOW,
                        actions=[ "sts:AssumeRole" ],
                        principals=[ aws_iam.ServicePrincipal("codepipeline.amazonaws.com") ]
                    )
                ]
            ),
            policies=[
                aws_iam.CfnRole.PolicyProperty(
                    policy_document=aws_iam.PolicyDocument(
                        statements=[
                            aws_iam.PolicyStatement(
                                effect=aws_iam.Effect.ALLOW,
                                actions=[
                                    "codebuild:BatchGetBuilds",
                                    "codebuild:StartBuild",
                                    "codedeploy:GetApplication",
                                    "codedeploy:GetDeploymentGroup",
                                    "codedeploy:ListApplications",
                                    "codedeploy:ListDeploymentGroups",
                                    "codepipeline:*",
                                    "iam:ListRoles",
                                    "iam:PassRole",
                                    "lambda:GetFunctionConfiguration",
                                    "lambda:ListFunctions",
                                    "s3:CreateBucket",
                                    "s3:GetBucketPolicy",
                                    "s3:GetObject",
                                    "s3:ListAllMyBuckets",
                                    "s3:ListBucket",
                                    "s3:PutBucketPolicy"
                                ],
                                resources=[ "*" ]
                            )
                        ]
                    ),
                    policy_name="CodePipelinePerms"
                )
            ]
        )
        codepipeline_role_arn = Arn.format(
            components=ArnComponents(
                account=Aws.ACCOUNT_ID,
                region="",
                resource="role",
                resource_name=codepipeline_role.ref,
                service="iam"
            ),
            stack=self
        )
        codepipeline_source_stage_role = aws_iam.CfnRole(
            self,
            "SourceStageRole",
            assume_role_policy_document=aws_iam.PolicyDocument(
                statements=[
                    aws_iam.PolicyStatement(
                        effect=aws_iam.Effect.ALLOW,
                        actions=[ "sts:AssumeRole" ],
                        principals=[ aws_iam.ArnPrincipal(codepipeline_role_arn) ]
                    )
                ],
            ),
            policies=[
                aws_iam.CfnRole.PolicyProperty(
                    policy_document=aws_iam.PolicyDocument(
                        statements=[
                            aws_iam.PolicyStatement(
                                effect=aws_iam.Effect.ALLOW,
                                actions=[
                                    "s3:Get*",
                                    "s3:Head*"
                                ],
                                resources=[ source_artifact_object_key_arn ]
                            ),
                            aws_iam.PolicyStatement(
                                effect=aws_iam.Effect.ALLOW,
                                actions=[ "s3:GetBucketVersioning" ],
                                resources=[
                                    Arn.format(
                                        components=ArnComponents(
                                            account="",
                                            region="",
                                            resource=source_artifact_bucket_name,
                                            service="s3"
                                        ),
                                        stack=self
                                    )
                                ]
                            ),
                            aws_iam.PolicyStatement(
                                effect=aws_iam.Effect.ALLOW,
                                actions=[ "s3:*" ],
                                resources=[ pipeline_artifact_bucket_arn ]
                            )
                        ]
                    ),
                    policy_name="SourceRolePerms"
                )
            ]
        )
        codepipeline_source_stage_role_arn = Arn.format(
            components=ArnComponents(
                account=Aws.ACCOUNT_ID,
                region="",
                resource="role",
                resource_name=codepipeline_source_stage_role.ref,
                service="iam"
            ),
            stack=self
        )
        codepipeline_deploy_stage_role = aws_iam.CfnRole(
            self,
            "DeployStageRole",
            assume_role_policy_document=aws_iam.PolicyDocument(
                statements=[
                    aws_iam.PolicyStatement(
                        effect=aws_iam.Effect.ALLOW,
                        actions=[ "sts:AssumeRole" ],
                        principals= [ aws_iam.ArnPrincipal(codepipeline_role_arn) ]
                    )
                ]
            ),
            policies=[
                aws_iam.CfnRole.PolicyProperty(
                    policy_document=aws_iam.PolicyDocument(
                        statements=[
                            aws_iam.PolicyStatement(
                                effect=aws_iam.Effect.ALLOW,
                                actions=[ "codedeploy:*" ],
                                resources=[ "*" ]
                            ),
                            aws_iam.PolicyStatement(
                                effect=aws_iam.Effect.ALLOW,
                                actions=[
                                    "s3:Get*",
                                    "s3:Head*",
                                    "s3:PutObject"
                                ],
                                resources=[ pipeline_artifact_bucket_arn ]
                            )
                        ]
                    ),
                    policy_name="DeployRolePerms"
                )
            ]
        )
        codepipeline_deploy_stage_role_arn = Arn.format(
            components=ArnComponents(
                account=Aws.ACCOUNT_ID,
                region="",
                resource="role",
                resource_name=codepipeline_deploy_stage_role.ref,
                service="iam"
            ),
            stack=self
        )
        codepipeline_finalize_stage_role = aws_iam.CfnRole(
           self,
           "CodePipelineFinalizeStageRole",
            assume_role_policy_document=aws_iam.PolicyDocument(
                statements=[
                    aws_iam.PolicyStatement(
                        effect=aws_iam.Effect.ALLOW,
                        actions=[ "sts:AssumeRole" ],
                        principals=[ aws_iam.ArnPrincipal(codepipeline_role_arn) ]
                    )
                ]
            ),
            policies=[
                aws_iam.CfnRole.PolicyProperty(
                    policy_document=aws_iam.PolicyDocument(
                        statements=[
                            aws_iam.PolicyStatement(
                                effect=aws_iam.Effect.ALLOW,
                                actions=[ "codedeploy:*" ],
                                resources=[ "*" ]
                            )
                        ]
                    ),
                    policy_name="CodeDeploy"
                ),
                aws_iam.CfnRole.PolicyProperty(
                    policy_document=aws_iam.PolicyDocument(
                        statements=[
                            aws_iam.PolicyStatement(
                                effect=aws_iam.Effect.ALLOW,
                                actions=[ "lambda:InvokeFunction" ],
                                resources=[ cloudfront_invalidation_lambda_function.attr_arn ]
                            )
                        ]
                    ),
                    policy_name="InvokeCloudFrontInvalidationLambdaFunction",
                )
            ]
        )
        codepipeline_finalize_stage_role.cfn_options.condition = cloudfront_enable_condition
        codepipeline_finalize_stage_role_arn = Arn.format(
            components=ArnComponents(
                account=Aws.ACCOUNT_ID,
                region="",
                resource="role",
                resource_name=codepipeline_finalize_stage_role.ref,
                service="iam"
            ),
            stack=self
        )

        codedeploy_application = aws_codedeploy.CfnApplication(
            self,
            "CodeDeployApplication",
            application_name=Aws.STACK_NAME,
            compute_platform="Server"
        )
        codedeploy_role = aws_iam.CfnRole(
             self,
            "CodeDeployRole",
            assume_role_policy_document=aws_iam.PolicyDocument(
                statements=[
                    aws_iam.PolicyStatement(
                        effect=aws_iam.Effect.ALLOW,
                        actions=[ "sts:AssumeRole" ],
                        principals=[ aws_iam.ServicePrincipal("codedeploy.{}.amazonaws.com".format(Aws.REGION)) ]
                    )
                ]
            ),
            policies=[
                aws_iam.CfnRole.PolicyProperty(
                    policy_document=aws_iam.PolicyDocument(
                        statements=[
                            aws_iam.PolicyStatement(
                                effect=aws_iam.Effect.ALLOW,
                                actions=[
                                    "s3:GetObject",
                                    "s3:PutObject"
                                ],
                                resources=[ pipeline_artifact_bucket_arn ]
                            ),
                        ]
                    ),
                    policy_name="DeployRolePermssions"
                )
            ],
            managed_policy_arns=[ "arn:aws:iam::aws:policy/service-role/AWSCodeDeployRole" ]
        )
        codedeploy_role_arn = Arn.format(
            components=ArnComponents(
                account=Aws.ACCOUNT_ID,
                region="",
                resource="role",
                resource_name=codedeploy_role.ref,
                service="iam"
            ),
            stack=self
        )
        codedeploy_deployment_group = aws_codedeploy.CfnDeploymentGroup(
            self,
            "CodeDeployDeploymentGroup",
            application_name=codedeploy_application.application_name,
            auto_scaling_groups=[ asg.asg.ref ],
            deployment_group_name="{}-app".format(Aws.STACK_NAME),
            deployment_config_name=aws_codedeploy.ServerDeploymentConfig.ALL_AT_ONCE.deployment_config_name,
            service_role_arn=codedeploy_role_arn,
            trigger_configurations=[
                aws_codedeploy.CfnDeploymentGroup.TriggerConfigProperty(
                    trigger_events=[
                        "DeploymentSuccess",
                        "DeploymentRollback"
                    ],
                    trigger_name="DeploymentNotification",
                    trigger_target_arn=notification_topic.ref
                )
            ]
        )
        codepipeline = aws_codepipeline.CfnPipeline(
            self,
            "Pipeline",
            artifact_store=aws_codepipeline.CfnPipeline.ArtifactStoreProperty(
                location=Token.as_string(
                    Fn.condition_if(
                        pipeline_artifact_bucket_name_exists_condition.logical_id,
                        pipeline_artifact_bucket_name_param.value_as_string,
                        pipeline_artifact_bucket.ref
                    )
                ),
                type="S3"
            ),
            role_arn=codepipeline_role_arn,
            stages=[
                aws_codepipeline.CfnPipeline.StageDeclarationProperty(
                    name="Source",
                    actions=[
                        aws_codepipeline.CfnPipeline.ActionDeclarationProperty(
                            action_type_id=aws_codepipeline.CfnPipeline.ActionTypeIdProperty(
                                category="Source",
                                owner="AWS",
                                provider="S3",
                                version="1"
                            ),
                            configuration={
                                "S3Bucket": source_artifact_bucket_name,
                                "S3ObjectKey": source_artifact_object_key_param.value_as_string
                            },
                            output_artifacts=[
                                aws_codepipeline.CfnPipeline.OutputArtifactProperty(
                                    name="build"
                                )
                            ],
                            name="SourceAction",
                            role_arn=codepipeline_source_stage_role_arn
                        )
                    ]
                ),
                aws_codepipeline.CfnPipeline.StageDeclarationProperty(
                    name="Transform",
                    actions=[
                        aws_codepipeline.CfnPipeline.ActionDeclarationProperty(
                            action_type_id=aws_codepipeline.CfnPipeline.ActionTypeIdProperty(
                                category="Build",
                                owner="AWS",
                                provider="CodeBuild",
                                version="1"
                            ),
                            configuration={
                                "ProjectName": codebuild_transform_project.ref
                            },
                            input_artifacts=[
                                aws_codepipeline.CfnPipeline.InputArtifactProperty(
                                    name="build",
                                )
                            ],
                            name="TransformAction",
                            output_artifacts=[
                                aws_codepipeline.CfnPipeline.OutputArtifactProperty(
                                    name="transformed"
                                )
                            ]
                        )
                    ]
                ),
                aws_codepipeline.CfnPipeline.StageDeclarationProperty(
                    name="Deploy",
                    actions=[
                        aws_codepipeline.CfnPipeline.ActionDeclarationProperty(
                            action_type_id=aws_codepipeline.CfnPipeline.ActionTypeIdProperty(
                                category="Deploy",
                                owner="AWS",
                                provider="CodeDeploy",
                                version="1"
                            ),
                            configuration={
                                "ApplicationName": codedeploy_application.ref,
                                "DeploymentGroupName": codedeploy_deployment_group.ref,
                            },
                            input_artifacts=[
                                aws_codepipeline.CfnPipeline.InputArtifactProperty(
                                    name="transformed"
                                )
                            ],
                            name="DeployAction",
                            role_arn=codepipeline_deploy_stage_role_arn
                        )
                    ]
                )
            ]
        )
        # https://github.com/aws/aws-cdk/issues/8396
        codepipeline.add_override(
            "Properties.Stages.3",
            {
                "Fn::If": [
                    cloudfront_enable_condition.logical_id,
                    {
                        "Actions": [
                            {
                                "ActionTypeId": {
                                    "Category": "Invoke",
                                    "Owner": "AWS",
                                    "Provider": "Lambda",
                                    "Version": "1"
                                },
                                "Configuration": {
                                    "FunctionName": cloudfront_invalidation_lambda_function.ref
                                },
                                "Name": "CloudFrontInvalidationAction",
                                "RoleArn": codepipeline_finalize_stage_role_arn
                            }
                        ],
                        "Name": "Finalize"
                    },
                    Aws.NO_VALUE
                ]
            }
        )
        cloudfront_invalidation_lambda_permission = aws_lambda.CfnPermission(
            self,
            "CloudFrontInvalidationLambdaPermission",
            action="lambda:InvokeFunction",
            function_name=cloudfront_invalidation_lambda_function.attr_arn,
            principal="events.amazonaws.com",
            source_arn=codepipeline_role_arn
        )
        cloudfront_invalidation_lambda_permission.cfn_options.condition = cloudfront_enable_condition

        # default drupal
        initialize_default_drupal_lambda_function_role = aws_iam.CfnRole(
            self,
            "InitializeDefaultDrupalLambdaFunctionRole",
            assume_role_policy_document=aws_iam.PolicyDocument(
                statements=[
                    aws_iam.PolicyStatement(
                        effect=aws_iam.Effect.ALLOW,
                        actions=[ "sts:AssumeRole" ],
                        principals=[ aws_iam.ServicePrincipal("lambda.amazonaws.com") ]
                    )
                ]
            ),
            managed_policy_arns=[
                "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
            ],
            policies=[
                # OE default drupal artifact should be public, so no policy needed for s3:GetObject
                aws_iam.CfnRole.PolicyProperty(
                    policy_document=aws_iam.PolicyDocument(
                        statements=[
                            aws_iam.PolicyStatement(
                                effect=aws_iam.Effect.ALLOW,
                                actions=[ "s3:ListBucket" ],
                                resources=[ source_artifact_bucket_arn ]
                            ),
                            aws_iam.PolicyStatement(
                                effect=aws_iam.Effect.ALLOW,
                                actions=[
                                    "s3:HeadObject",
                                    "s3:PutObject"
                                ],
                                resources=[ source_artifact_object_key_arn ]
                            )
                        ]
                    ),
                    policy_name="PutDefaultDrupalArtifact"
                ),
                aws_iam.CfnRole.PolicyProperty(
                    policy_document=iam_notification_publish_policy,
                    policy_name="SnsPublishToNotificationTopic"
                )
            ]
        )
        initialize_default_drupal_lambda_function_role.cfn_options.condition = initialize_default_drupal_condition
        with open("drupal/initialize_default_drupal_lambda_function_code.py") as f:
            initialize_default_drupal_lambda_function_code = f.read()
        initialize_default_drupal_lambda_function = aws_lambda.CfnFunction(
            self,
            "InitializeDefaultDrupalLambdaFunction",
            code=aws_lambda.CfnFunction.CodeProperty(
                zip_file=initialize_default_drupal_lambda_function_code
            ),
            dead_letter_config=aws_lambda.CfnFunction.DeadLetterConfigProperty(
                target_arn=notification_topic.ref
            ),
            environment=aws_lambda.CfnFunction.EnvironmentProperty(
                variables={
                    "DefaultDrupalSourceUrl": DEFAULT_DRUPAL_SOURCE_URL,
                    "SourceArtifactBucket": source_artifact_bucket_name,
                    "SourceArtifactObjectKey": source_artifact_object_key_param.value_as_string,
                    "StackName": Aws.STACK_NAME
                }
            ),
            handler="index.lambda_handler",
            role=initialize_default_drupal_lambda_function_role.attr_arn,
            runtime="python3.7",
            timeout=300
        )
        initialize_default_drupal_lambda_function.cfn_options.condition = initialize_default_drupal_condition
        initialize_default_drupal_custom_resource = aws_cloudformation.CfnCustomResource(
            self,
            "InitializeDefaultDrupalCustomResource",
            service_token=initialize_default_drupal_lambda_function.attr_arn
        )
        initialize_default_drupal_custom_resource.cfn_options.condition = initialize_default_drupal_condition

        #
        # OUTPUTS
        #

        alb_dns_name_output = CfnOutput(
            self,
            "AlbDnsNameOutput",
            description="The DNS name of the application load balancer.",
            value=alb.alb.attr_dns_name
        )
        cloudfront_distribution_endpoint_output = CfnOutput(
            self,
            "CloudFrontDistributionEndpointOutput",
            condition=cloudfront_enable_condition,
            description="The distribution DNS name endpoint for connection. Configure in Drupal's settings.php.",
            value=cloudfront_distribution.attr_domain_name
        )
        elasticache_cluster_endpoint_output = CfnOutput(
            self,
            "ElastiCacheClusterEndpointOutput",
            condition=elasticache_enable_condition,
            description="The endpoint of the cluster for connection. Configure in Drupal's settings.php.",
            value="{}:{}".format(elasticache_cluster.attr_configuration_endpoint_address,
                                 elasticache_cluster.attr_configuration_endpoint_port)
        )
        source_artifact_bucket_name_output = CfnOutput(
            self,
            "SourceArtifactBucketNameOutput",
            value=source_artifact_bucket_name
        )
        
        parameter_groups = [
            {
                "Label": {
                    "default": "CI/CD"
                },
                "Parameters": [
                    notification_email_param.logical_id,
                    source_artifact_bucket_name_param.logical_id,
                    source_artifact_object_key_param.logical_id
                ]
            },
            {
                "Label": {
                    "default": "Data Snapshots"
                },
                "Parameters": [
                    db_snapshot_identifier_param.logical_id,
                    db_instance_class_param.logical_id
                ]
            },
            {
                "Label": {
                    "default": "Application Config"
                },
                "Parameters": [
                    secret_arn_param.logical_id,
                    initialize_default_drupal_param.logical_id
                ]
            },
            {
                "Label": {
                    "default": "ElastiCache memcached"
                },
                "Parameters": [
                    elasticache_enable_param.logical_id,
                    elasticache_cluster_engine_version_param.logical_id,
                    elasticache_cluster_cache_node_type_param.logical_id,
                    elasticache_cluster_num_cache_nodes_param.logical_id
                ]
            },
            {
                "Label": {
                    "default": "CloudFront"
                },
                "Parameters": [
                    cloudfront_enable_param.logical_id,
                    cloudfront_certificate_arn_param.logical_id,
                    cloudfront_aliases_param.logical_id,
                    cloudfront_price_class_param.logical_id
                ]
            }
        ]
        parameter_groups += vpc.metadata_parameter_group()
        parameter_groups += [
            {
                "Label": {
                    "default": "Template Development"
                },
                "Parameters": [
                    pipeline_artifact_bucket_name_param.logical_id
                ]
            }
        ]

        # AWS::CloudFormation::Interface
        self.template_options.metadata = {
            "OE::Patterns::TemplateVersion": template_version,
            "AWS::CloudFormation::Interface": {
                "ParameterGroups": parameter_groups,
                "ParameterLabels": {
                    cloudfront_aliases_param.logical_id: {
                        "default": "CloudFront Aliases"
                    },
                    cloudfront_certificate_arn_param.logical_id: {
                        "default": "CloudFront ACM Certificate ARN"
                    },
                    cloudfront_enable_param.logical_id: {
                        "default": "Enable CloudFront"
                    },
                    cloudfront_price_class_param.logical_id: {
                        "default": "CloudFront Price Class"
                    },
                    db_snapshot_identifier_param.logical_id: {
                        "default": "RDS Snapshot Identifier"
                    },
                    db_instance_class_param.logical_id: {
                        "default": "RDS Instance Class"
                    },
                    elasticache_cluster_cache_node_type_param.logical_id: {
                        "default": "ElastiCache Cache Node Type"
                    },
                    elasticache_cluster_engine_version_param.logical_id: {
                        "default": "ElastiCache Engine Version"
                    },
                    elasticache_cluster_num_cache_nodes_param.logical_id: {
                        "default": "ElastiCache Num Nodes"
                    },
                    elasticache_enable_param.logical_id: {
                        "default": "Enable ElastiCache"
                    },
                    initialize_default_drupal_param.logical_id: {
                        "default": "Initialize with a default Drupal codebase"
                    },
                    notification_email_param.logical_id: {
                        "default": "Notification Email"
                    },
                    pipeline_artifact_bucket_name_param.logical_id: {
                        "default": "CodePipeline Bucket Name"
                    },
                    secret_arn_param.logical_id: {
                        "default": "SecretsManager secret ARN"
                    },
                    source_artifact_bucket_name_param.logical_id: {
                        "default": "Source Artifact S3 Bucket Name"
                    },
                    source_artifact_object_key_param.logical_id: {
                        "default": "Source Artifact S3 Object Key (path)"
                    },
                    **vpc.metadata_parameter_labels()
                }
            }
        }
