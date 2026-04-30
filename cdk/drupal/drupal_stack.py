import os
import subprocess

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
    aws_iam,
    aws_lambda,
    aws_s3,
    aws_sns,
    aws_ssm,
    CfnCondition,
    CfnDeletionPolicy,
    CfnOutput,
    CfnParameter,
    Fn,
    Stack,
    Token
)
from constructs import Construct

from oe_patterns_cdk_common.alb import Alb
from oe_patterns_cdk_common.asg import Asg
from oe_patterns_cdk_common.aurora_cluster import AuroraMysql
from oe_patterns_cdk_common.db_secret import DbSecret
from oe_patterns_cdk_common.dns import Dns
from oe_patterns_cdk_common.efs import Efs
from oe_patterns_cdk_common.elasticache_cluster import ElasticacheMemcached
from oe_patterns_cdk_common.util import Util
from oe_patterns_cdk_common.vpc import Vpc

if 'TEMPLATE_VERSION' in os.environ:
    template_version = os.environ['TEMPLATE_VERSION']
else:
    try:
        template_version = subprocess.check_output(["git", "describe"]).strip().decode('ascii')
    except Exception:
        template_version = "CICD"

# Updated each release in Phase 3 (dev AMI) and Phase 6 prereqs (prod AMI).
AMI_ID = "ami-03e7ffa59e6af18f4"  # ordinary-experts-patterns-drupal-3.0.0-20260429
NEXT_RELEASE_PREFIX = "v300"

# URL of a default Drupal codebase ZIP, copied into the source bucket when
# InitializeDefaultDrupal=true. Built from the `aws-marketplace-oe-patterns-
# drupal-example-site` repo at the matching tag. Users override this via the
# DefaultDrupalSourceUrl stack parameter when they have their own codebase.
DEFAULT_DRUPAL_SOURCE_URL = "https://ordinary-experts-aws-marketplace-drupal-pattern-artifacts.s3.amazonaws.com/aws-marketplace-oe-patterns-drupal-example-site/refs/tags/2.0.0.zip"


class DrupalStack(Stack):

    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        #
        # PARAMETERS (Drupal-specific only — common constructs add their own)
        #

        cloudfront_aliases_param = CfnParameter(
            self,
            "CloudFrontAliases",
            default="",
            description="Optional: Comma-delimited list of hostname aliases registered with the CloudFront distribution. If a certificate is supplied, each hostname must validate against the certificate.",
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
            allowed_values=["true", "false"],
            default="false",
            description="Required: Enable CloudFront CDN support."
        )
        cloudfront_price_class_param = CfnParameter(
            self,
            "CloudFrontPriceClass",
            allowed_values=["PriceClass_All", "PriceClass_200", "PriceClass_100"],
            default="PriceClass_All",
            description="Required: Price class to use for CloudFront CDN (only applies when CloudFront enabled)."
        )
        default_drupal_source_url_param = CfnParameter(
            self,
            "DefaultDrupalSourceUrl",
            default=DEFAULT_DRUPAL_SOURCE_URL,
            description="Optional: URL of a Drupal codebase ZIP to seed the source bucket with (only used when InitializeDefaultDrupal=true). Leave blank if uploading your own codebase to the source bucket."
        )
        initialize_default_drupal_param = CfnParameter(
            self,
            "InitializeDefaultDrupal",
            allowed_values=["true", "false"],
            default="true",
            description="Optional: Trigger the first deployment by copying DefaultDrupalSourceUrl into the source bucket. Set to false if uploading your own Drupal codebase to the source bucket."
        )
        notification_email_param = CfnParameter(
            self,
            "NotificationEmail",
            default="",
            description="Optional: Email address that receives deploy and lambda-error notifications. Used only by this stack to subscribe to an SNS topic; not sent to any third party."
        )
        pipeline_artifact_bucket_name_param = CfnParameter(
            self,
            "PipelineArtifactBucketName",
            default="",
            description="Optional: Use an existing S3 bucket for CodePipeline artifacts. Must be in this AWS account."
        )
        source_artifact_bucket_name_param = CfnParameter(
            self,
            "SourceArtifactBucketName",
            default="",
            description="Optional: Use an existing S3 bucket for application build artifacts. If empty, a bucket is created."
        )
        source_artifact_object_key_param = CfnParameter(
            self,
            "SourceArtifactObjectKey",
            default="drupal.zip",
            description="Required: S3 object key (path) for the application build artifact. Updates to this object trigger a deployment."
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
        initialize_default_drupal_condition = CfnCondition(
            self,
            "InitializeDefaultDrupalCondition",
            expression=Fn.condition_equals(initialize_default_drupal_param.value, "true")
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
        # SHARED RESOURCES
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
        pipeline_artifact_bucket.cfn_options.condition = pipeline_artifact_bucket_name_not_exists_condition
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
            versioning_configuration=aws_s3.CfnBucket.VersioningConfigurationProperty(status="Enabled")
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

        # vpc / dns
        vpc = Vpc(self, "Vpc")
        dns = Dns(self, "Dns")

        # database
        db_secret = DbSecret(self, "DbSecret")
        db = AuroraMysql(self, "Db", db_secret=db_secret, vpc=vpc, database_name="drupal")

        # memcached (always provisioned — minimum cost ~$20/mo at default cache.t4g.micro x2)
        # Default to 2 nodes because cdk-common ElasticacheMemcached hard-codes
        # az_mode="cross-az" which AWS rejects with num_cache_nodes=1.
        memcached = ElasticacheMemcached(self, "ElastiCache", vpc=vpc)
        memcached.elasticache_cluster_num_cache_nodes_param.default = 2

        # notifications
        notification_topic = aws_sns.CfnTopic(
            self,
            "NotificationTopic",
            topic_name=Fn.join("-", [Aws.STACK_NAME, "notifications", Fn.select(2, Fn.split("/", Aws.STACK_ID))])
        )
        notification_subscription = aws_sns.CfnSubscription(
            self,
            "NotificationSubscription",
            protocol="email",
            topic_arn=notification_topic.ref,
            endpoint=notification_email_param.value_as_string
        )
        notification_subscription.cfn_options.condition = notification_email_exists_condition
        iam_notification_publish_policy = aws_iam.PolicyDocument(
            statements=[
                aws_iam.PolicyStatement(
                    effect=aws_iam.Effect.ALLOW,
                    actions=["sns:Publish"],
                    resources=[notification_topic.ref]
                )
            ]
        )

        # ASG
        with open("drupal/app_launch_config_user_data.sh") as f:
            app_launch_config_user_data = f.read()
        asg = Asg(
            self,
            "Asg",
            ami_id=AMI_ID,
            ami_id_param_name_suffix=NEXT_RELEASE_PREFIX,
            secret_arns=[db_secret.secret_arn()],
            deployment_rolling_update=True,
            pipeline_bucket_arn=pipeline_artifact_bucket_arn,
            use_graviton=False,
            user_data_contents=app_launch_config_user_data,
            user_data_variables={
                "CloudFrontHostnameParameterName": Aws.STACK_NAME + "-cloudfront-hostname",
                "DrupalSalt": Fn.base64(Aws.STACK_ID),
                "Hostname": dns.hostname(),
                "DbSecretArn": db_secret.secret_arn()
            },
            vpc=vpc
        )

        # ALB + DNS wiring
        alb = Alb(self, "Alb", asg=asg, vpc=vpc)
        asg.asg.target_group_arns = [alb.target_group.ref]
        dns.add_alb(alb)

        # EFS for /sites/default/files
        efs = Efs(self, "Efs", app_sg=asg.sg, vpc=vpc)

        # security group ingress
        Util.add_sg_ingress(db, asg.sg)
        Util.add_sg_ingress(memcached, asg.sg)

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
                    allowed_methods=["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"],
                    compress=True,
                    default_ttl=86400,
                    forwarded_values=aws_cloudfront.CfnDistribution.ForwardedValuesProperty(
                        cookies=aws_cloudfront.CfnDistribution.CookiesProperty(
                            forward="whitelist",
                            whitelisted_names=["SESS*", "SSESS*"]
                        ),
                        headers=["CloudFront-Forwarded-Proto", "Host", "Origin"],
                        query_string=True
                    ),
                    min_ttl=0,
                    max_ttl=31536000,
                    target_origin_id="alb",
                    viewer_protocol_policy="redirect-to-https"
                ),
                enabled=True,
                origins=[
                    aws_cloudfront.CfnDistribution.OriginProperty(
                        domain_name=alb.alb.attr_dns_name,
                        id="alb",
                        custom_origin_config=aws_cloudfront.CfnDistribution.CustomOriginConfigProperty(
                            origin_protocol_policy="https-only",
                            origin_ssl_protocols=["TLSv1.1", "TLSv1.2"]
                        )
                    )
                ],
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

        cloudfront_hostname_param = aws_ssm.CfnParameter(
            self,
            "CloudFrontHostnameParameter",
            type="String",
            value=Token.as_string(
                Fn.condition_if(
                    cloudfront_enable_condition.logical_id,
                    Fn.condition_if(
                        cloudfront_aliases_exist_condition.logical_id,
                        Fn.select(0, cloudfront_aliases_param.value_as_list),
                        cloudfront_distribution.attr_domain_name
                    ),
                    ""
                )
            ),
            name=Aws.STACK_NAME + "-cloudfront-hostname"
        )
        cloudfront_hostname_param.cfn_options.condition = cloudfront_enable_condition

        cloudfront_invalidation_lambda_function_role = aws_iam.CfnRole(
            self,
            "CloudFrontInvalidationLambdaFunctionRole",
            assume_role_policy_document=aws_iam.PolicyDocument(
                statements=[
                    aws_iam.PolicyStatement(
                        effect=aws_iam.Effect.ALLOW,
                        actions=["sts:AssumeRole"],
                        principals=[aws_iam.ServicePrincipal("lambda.amazonaws.com")]
                    )
                ]
            ),
            managed_policy_arns=["arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"],
            policies=[
                aws_iam.CfnRole.PolicyProperty(
                    policy_document=aws_iam.PolicyDocument(
                        statements=[
                            aws_iam.PolicyStatement(
                                effect=aws_iam.Effect.ALLOW,
                                actions=["cloudfront:CreateInvalidation"],
                                resources=[cloudfront_distribution_arn]
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
                                actions=["codepipeline:PutJobSuccessResult", "codepipeline:PutJobFailureResult"],
                                resources=["*"]
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
            code=aws_lambda.CfnFunction.CodeProperty(zip_file=cloudfront_invalidation_lambda_function_code),
            dead_letter_config=aws_lambda.CfnFunction.DeadLetterConfigProperty(target_arn=notification_topic.ref),
            environment=aws_lambda.CfnFunction.EnvironmentProperty(
                variables={"CloudFrontDistributionId": cloudfront_distribution.ref}
            ),
            handler="index.lambda_handler",
            role=cloudfront_invalidation_lambda_function_role.attr_arn,
            runtime="python3.12"
        )
        cloudfront_invalidation_lambda_function.cfn_options.condition = cloudfront_enable_condition

        # codebuild
        codebuild_transform_service_role = aws_iam.CfnRole(
            self,
            "CodeBuildTransformServiceRole",
            assume_role_policy_document=aws_iam.PolicyDocument(
                statements=[
                    aws_iam.PolicyStatement(
                        effect=aws_iam.Effect.ALLOW,
                        actions=["sts:AssumeRole"],
                        principals=[aws_iam.ServicePrincipal("codebuild.amazonaws.com")]
                    )
                ]
            ),
            policies=[
                aws_iam.CfnRole.PolicyProperty(
                    policy_document=aws_iam.PolicyDocument(
                        statements=[
                            aws_iam.PolicyStatement(
                                effect=aws_iam.Effect.ALLOW,
                                actions=["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
                                resources=["*"]
                            ),
                            aws_iam.PolicyStatement(
                                effect=aws_iam.Effect.ALLOW,
                                actions=["s3:GetObject", "s3:PutObject"],
                                resources=[pipeline_artifact_bucket_arn]
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
            artifacts=aws_codebuild.CfnProject.ArtifactsProperty(type="CODEPIPELINE"),
            environment=aws_codebuild.CfnProject.EnvironmentProperty(
                compute_type="BUILD_GENERAL1_SMALL",
                environment_variables=[
                    aws_codebuild.CfnProject.EnvironmentVariableProperty(
                        name="AUTO_SCALING_GROUP_NAME",
                        value=asg.asg.ref
                    )
                ],
                image="aws/codebuild/standard:7.0",
                type="LINUX_CONTAINER"
            ),
            name="{}-transform".format(Aws.STACK_NAME),
            service_role=codebuild_transform_service_role_arn,
            source=aws_codebuild.CfnProject.SourceProperty(
                build_spec=codebuild_transform_project_buildspec,
                type="CODEPIPELINE"
            )
        )

        # codedeploy
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
                        actions=["sts:AssumeRole"],
                        principals=[aws_iam.ServicePrincipal("codedeploy.{}.amazonaws.com".format(Aws.REGION))]
                    )
                ]
            ),
            policies=[
                aws_iam.CfnRole.PolicyProperty(
                    policy_document=aws_iam.PolicyDocument(
                        statements=[
                            aws_iam.PolicyStatement(
                                effect=aws_iam.Effect.ALLOW,
                                actions=["s3:GetObject", "s3:PutObject"],
                                resources=[pipeline_artifact_bucket_arn]
                            )
                        ]
                    ),
                    policy_name="DeployRolePermssions"
                )
            ],
            managed_policy_arns=["arn:aws:iam::aws:policy/service-role/AWSCodeDeployRole"]
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
            auto_scaling_groups=[asg.asg.ref],
            deployment_group_name="{}-app".format(Aws.STACK_NAME),
            deployment_config_name=aws_codedeploy.ServerDeploymentConfig.ALL_AT_ONCE.deployment_config_name,
            service_role_arn=codedeploy_role_arn,
            trigger_configurations=[
                aws_codedeploy.CfnDeploymentGroup.TriggerConfigProperty(
                    trigger_events=["DeploymentSuccess", "DeploymentRollback"],
                    trigger_name="DeploymentNotification",
                    trigger_target_arn=notification_topic.ref
                )
            ]
        )

        # codepipeline
        codepipeline_role = aws_iam.CfnRole(
            self,
            "PipelineRole",
            assume_role_policy_document=aws_iam.PolicyDocument(
                statements=[
                    aws_iam.PolicyStatement(
                        effect=aws_iam.Effect.ALLOW,
                        actions=["sts:AssumeRole"],
                        principals=[aws_iam.ServicePrincipal("codepipeline.amazonaws.com")]
                    )
                ]
            )
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
                        actions=["sts:AssumeRole"],
                        principals=[aws_iam.ArnPrincipal(codepipeline_role_arn)]
                    )
                ]
            ),
            policies=[
                aws_iam.CfnRole.PolicyProperty(
                    policy_document=aws_iam.PolicyDocument(
                        statements=[
                            aws_iam.PolicyStatement(
                                effect=aws_iam.Effect.ALLOW,
                                actions=["s3:Get*", "s3:Head*"],
                                resources=[source_artifact_object_key_arn]
                            ),
                            aws_iam.PolicyStatement(
                                effect=aws_iam.Effect.ALLOW,
                                actions=["s3:GetBucketVersioning"],
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
                                actions=["s3:GetObject", "s3:PutObject"],
                                resources=[pipeline_artifact_bucket_arn]
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
        codepipeline_transform_stage_role = aws_iam.CfnRole(
            self,
            "TransformStageRole",
            assume_role_policy_document=aws_iam.PolicyDocument(
                statements=[
                    aws_iam.PolicyStatement(
                        effect=aws_iam.Effect.ALLOW,
                        actions=["sts:AssumeRole"],
                        principals=[aws_iam.ArnPrincipal(codepipeline_role_arn)]
                    )
                ]
            ),
            policies=[
                aws_iam.CfnRole.PolicyProperty(
                    policy_document=aws_iam.PolicyDocument(
                        statements=[
                            aws_iam.PolicyStatement(
                                effect=aws_iam.Effect.ALLOW,
                                actions=["codebuild:BatchGetBuilds", "codebuild:StartBuild"],
                                resources=[codebuild_transform_project.attr_arn]
                            )
                        ]
                    ),
                    policy_name="TransformRolePerms"
                )
            ]
        )
        codepipeline_transform_stage_role_arn = Arn.format(
            components=ArnComponents(
                account=Aws.ACCOUNT_ID,
                region="",
                resource="role",
                resource_name=codepipeline_transform_stage_role.ref,
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
                        actions=["sts:AssumeRole"],
                        principals=[aws_iam.ArnPrincipal(codepipeline_role_arn)]
                    )
                ]
            ),
            policies=[
                aws_iam.CfnRole.PolicyProperty(
                    policy_document=aws_iam.PolicyDocument(
                        statements=[
                            aws_iam.PolicyStatement(
                                effect=aws_iam.Effect.ALLOW,
                                actions=["codedeploy:GetApplication", "codedeploy:RegisterApplicationRevision"],
                                resources=[
                                    f"arn:{Aws.PARTITION}:codedeploy:{Aws.REGION}:{Aws.ACCOUNT_ID}:application:{codedeploy_application.application_name}"
                                ],
                                sid="codedeployapplication"
                            ),
                            aws_iam.PolicyStatement(
                                effect=aws_iam.Effect.ALLOW,
                                actions=["codedeploy:CreateDeployment", "codedeploy:GetDeployment", "codedeploy:GetDeploymentGroup"],
                                resources=[
                                    f"arn:{Aws.PARTITION}:codedeploy:{Aws.REGION}:{Aws.ACCOUNT_ID}:deploymentgroup:{codedeploy_application.application_name}/{codedeploy_deployment_group.deployment_group_name}"
                                ],
                                sid="codedeploydeploymentgroup"
                            ),
                            aws_iam.PolicyStatement(
                                effect=aws_iam.Effect.ALLOW,
                                actions=["s3:GetObject", "s3:PutObject"],
                                resources=[pipeline_artifact_bucket_arn]
                            ),
                            aws_iam.PolicyStatement(
                                effect=aws_iam.Effect.ALLOW,
                                actions=["codedeploy:GetDeploymentConfig"],
                                resources=[
                                    f"arn:{Aws.PARTITION}:codedeploy:{Aws.REGION}:{Aws.ACCOUNT_ID}:deploymentconfig:CodeDeployDefault.AllAtOnce"
                                ],
                                sid="codedeploydeploymentconfig"
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
                        actions=["sts:AssumeRole"],
                        principals=[aws_iam.ArnPrincipal(codepipeline_role_arn)]
                    )
                ]
            ),
            policies=[
                aws_iam.CfnRole.PolicyProperty(
                    policy_document=aws_iam.PolicyDocument(
                        statements=[
                            aws_iam.PolicyStatement(
                                effect=aws_iam.Effect.ALLOW,
                                actions=["lambda:InvokeFunction"],
                                resources=[cloudfront_invalidation_lambda_function.attr_arn]
                            )
                        ]
                    ),
                    policy_name="InvokeCloudFrontInvalidationLambdaFunction"
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
                                category="Source", owner="AWS", provider="S3", version="1"
                            ),
                            configuration={
                                "S3Bucket": source_artifact_bucket_name,
                                "S3ObjectKey": source_artifact_object_key_param.value_as_string
                            },
                            output_artifacts=[
                                aws_codepipeline.CfnPipeline.OutputArtifactProperty(name="build")
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
                                category="Build", owner="AWS", provider="CodeBuild", version="1"
                            ),
                            configuration={"ProjectName": codebuild_transform_project.ref},
                            input_artifacts=[
                                aws_codepipeline.CfnPipeline.InputArtifactProperty(name="build")
                            ],
                            name="TransformAction",
                            output_artifacts=[
                                aws_codepipeline.CfnPipeline.OutputArtifactProperty(name="transformed")
                            ],
                            role_arn=codepipeline_transform_stage_role_arn
                        )
                    ]
                ),
                aws_codepipeline.CfnPipeline.StageDeclarationProperty(
                    name="Deploy",
                    actions=[
                        aws_codepipeline.CfnPipeline.ActionDeclarationProperty(
                            action_type_id=aws_codepipeline.CfnPipeline.ActionTypeIdProperty(
                                category="Deploy", owner="AWS", provider="CodeDeploy", version="1"
                            ),
                            configuration={
                                "ApplicationName": codedeploy_application.ref,
                                "DeploymentGroupName": codedeploy_deployment_group.ref
                            },
                            input_artifacts=[
                                aws_codepipeline.CfnPipeline.InputArtifactProperty(name="transformed")
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

        # default-drupal initialization (optional, opt-in via InitializeDefaultDrupal=true)
        initialize_default_drupal_lambda_function_role = aws_iam.CfnRole(
            self,
            "InitializeDefaultDrupalLambdaFunctionRole",
            assume_role_policy_document=aws_iam.PolicyDocument(
                statements=[
                    aws_iam.PolicyStatement(
                        effect=aws_iam.Effect.ALLOW,
                        actions=["sts:AssumeRole"],
                        principals=[aws_iam.ServicePrincipal("lambda.amazonaws.com")]
                    )
                ]
            ),
            managed_policy_arns=["arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"],
            policies=[
                aws_iam.CfnRole.PolicyProperty(
                    policy_document=aws_iam.PolicyDocument(
                        statements=[
                            aws_iam.PolicyStatement(
                                effect=aws_iam.Effect.ALLOW,
                                actions=["s3:ListBucket"],
                                resources=[source_artifact_bucket_arn]
                            ),
                            aws_iam.PolicyStatement(
                                effect=aws_iam.Effect.ALLOW,
                                actions=["s3:HeadObject", "s3:PutObject"],
                                resources=[source_artifact_object_key_arn]
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
            code=aws_lambda.CfnFunction.CodeProperty(zip_file=initialize_default_drupal_lambda_function_code),
            dead_letter_config=aws_lambda.CfnFunction.DeadLetterConfigProperty(target_arn=notification_topic.ref),
            environment=aws_lambda.CfnFunction.EnvironmentProperty(
                variables={
                    "DefaultDrupalSourceUrl": default_drupal_source_url_param.value_as_string,
                    "SourceArtifactBucket": source_artifact_bucket_name,
                    "SourceArtifactObjectKey": source_artifact_object_key_param.value_as_string,
                    "StackName": Aws.STACK_NAME
                }
            ),
            handler="index.lambda_handler",
            role=initialize_default_drupal_lambda_function_role.attr_arn,
            runtime="python3.12",
            timeout=300
        )
        initialize_default_drupal_lambda_function.cfn_options.condition = initialize_default_drupal_condition
        initialize_default_drupal_custom_resource = aws_cloudformation.CfnCustomResource(
            self,
            "InitializeDefaultDrupalCustomResource",
            service_token=initialize_default_drupal_lambda_function.attr_arn
        )
        initialize_default_drupal_custom_resource.cfn_options.condition = initialize_default_drupal_condition

        # cross-resource dependencies
        asg.asg.node.add_dependency(db.db_primary_instance)

        #
        # OUTPUTS
        #

        CfnOutput(
            self,
            "AlbDnsNameOutput",
            description="The DNS name of the application load balancer.",
            value=alb.alb.attr_dns_name
        )
        CfnOutput(
            self,
            "CloudFrontDistributionEndpointOutput",
            condition=cloudfront_enable_condition,
            description="The CloudFront distribution domain name. Configure in Drupal's settings.php.",
            value=cloudfront_distribution.attr_domain_name
        )
        CfnOutput(
            self,
            "ElastiCacheClusterEndpointOutput",
            description="The memcached cluster configuration endpoint. Configure in Drupal's settings.php.",
            value="{}:{}".format(
                memcached.elasticache_cluster.attr_configuration_endpoint_address,
                memcached.elasticache_cluster.attr_configuration_endpoint_port
            )
        )
        CfnOutput(
            self,
            "SourceArtifactBucketNameOutput",
            value=source_artifact_bucket_name
        )

        #
        # CLOUDFORMATION INTERFACE METADATA
        #

        parameter_groups = [
            {
                "Label": {"default": "CI/CD"},
                "Parameters": [
                    notification_email_param.logical_id,
                    source_artifact_bucket_name_param.logical_id,
                    source_artifact_object_key_param.logical_id
                ]
            },
            {
                "Label": {"default": "Application Config"},
                "Parameters": [
                    initialize_default_drupal_param.logical_id,
                    default_drupal_source_url_param.logical_id
                ]
            },
            {
                "Label": {"default": "CloudFront"},
                "Parameters": [
                    cloudfront_enable_param.logical_id,
                    cloudfront_certificate_arn_param.logical_id,
                    cloudfront_aliases_param.logical_id,
                    cloudfront_price_class_param.logical_id
                ]
            }
        ]
        parameter_groups += alb.metadata_parameter_group()
        parameter_groups += dns.metadata_parameter_group()
        parameter_groups += db_secret.metadata_parameter_group()
        parameter_groups += db.metadata_parameter_group()
        parameter_groups += memcached.metadata_parameter_group()
        parameter_groups += asg.metadata_parameter_group()
        parameter_groups += efs.metadata_parameter_group()
        parameter_groups += vpc.metadata_parameter_group()
        parameter_groups += [
            {
                "Label": {"default": "Template Development"},
                "Parameters": [pipeline_artifact_bucket_name_param.logical_id]
            }
        ]

        self.template_options.metadata = {
            "OE::Patterns::TemplateVersion": template_version,
            "AWS::CloudFormation::Interface": {
                "ParameterGroups": parameter_groups,
                "ParameterLabels": {
                    cloudfront_aliases_param.logical_id: {"default": "CloudFront Aliases"},
                    cloudfront_certificate_arn_param.logical_id: {"default": "CloudFront ACM Certificate ARN"},
                    cloudfront_enable_param.logical_id: {"default": "Enable CloudFront"},
                    cloudfront_price_class_param.logical_id: {"default": "CloudFront Price Class"},
                    default_drupal_source_url_param.logical_id: {"default": "Default Drupal Source ZIP URL"},
                    initialize_default_drupal_param.logical_id: {"default": "Initialize with a default Drupal codebase"},
                    notification_email_param.logical_id: {"default": "Notification Email"},
                    pipeline_artifact_bucket_name_param.logical_id: {"default": "CodePipeline Bucket Name"},
                    source_artifact_bucket_name_param.logical_id: {"default": "Source Artifact S3 Bucket Name"},
                    source_artifact_object_key_param.logical_id: {"default": "Source Artifact S3 Object Key (path)"},
                    **alb.metadata_parameter_labels(),
                    **dns.metadata_parameter_labels(),
                    **db_secret.metadata_parameter_labels(),
                    **db.metadata_parameter_labels(),
                    **memcached.metadata_parameter_labels(),
                    **asg.metadata_parameter_labels(),
                    **efs.metadata_parameter_labels(),
                    **vpc.metadata_parameter_labels()
                }
            }
        }
