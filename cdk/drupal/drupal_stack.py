import json
from aws_cdk import (
    aws_autoscaling,
    aws_cloudfront,
    aws_codedeploy,
    aws_codepipeline,
    aws_codepipeline_actions,
    aws_ec2,
    aws_efs,
    aws_elasticache,
    aws_elasticloadbalancingv2,
    aws_iam,
    aws_logs,
    aws_rds,
    aws_s3,
    aws_secretsmanager,
    aws_sns,
    core
)

AMI="ami-020957f1bf92e5753"
DB_SNAPSHOT="arn:aws:rds:us-east-1:992593896645:cluster-snapshot:oe-patterns-drupal-default-20200504"
TWO_YEARS_IN_DAYS=731

class DrupalStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # TODO: Encryption
        # https://github.com/aws/aws-cdk/blob/v1.36.1/packages/@aws-cdk/aws-codepipeline/lib/pipeline.ts#L225-L244
        artifact_bucket = aws_s3.Bucket(
            self,
            "ArtifactBucket",
            access_control=aws_s3.BucketAccessControl.PRIVATE,
            block_public_access=aws_s3.BlockPublicAccess.BLOCK_ALL
        )

        source_artifact_s3_bucket_param = core.CfnParameter(
            self,
            "SourceArtifactS3Bucket",
            default="github-user-and-bucket-githubartifactbucket-1c9jk3sjkqv8p"
        )
        source_artifact_s3_object_key_param = core.CfnParameter(
            self,
            "SourceArtifactS3ObjectKey",
            default="aws-marketplace-oe-patterns-drupal-example-site/refs/heads/develop.tar.gz"
        )

        certificate_arn_param = core.CfnParameter(
            self,
            "CertificateArn",
            default=""
        )
        certificate_arn_exists_condition = core.CfnCondition(
            self,
            "CertificateArnExists",
            expression=core.Fn.condition_not(core.Fn.condition_equals(certificate_arn_param.value, ""))
        )
        certificate_arn_does_not_exist_condition = core.CfnCondition(
            self,
            "CertificateArnNotExists",
            expression=core.Fn.condition_equals(certificate_arn_param.value, "")
        )
        vpc = aws_ec2.Vpc(
            self,
            "Vpc",
            cidr="10.0.0.0/16"
        )
        app_sg = aws_ec2.SecurityGroup(
            self,
            "AppSg",
            vpc=vpc
        )
        db_sg = aws_ec2.SecurityGroup(
            self,
            "DBSg",
            vpc=vpc
        )
        db_sg.add_ingress_rule(
            peer=app_sg,
            connection=aws_ec2.Port.tcp(3306)
        )
        db_subnet_group = aws_rds.CfnDBSubnetGroup(
            self,
            "DBSubnetGroup",
            db_subnet_group_description="test",
            subnet_ids=vpc.select_subnets(subnet_type=aws_ec2.SubnetType.PRIVATE).subnet_ids
        )
        db_cluster_parameter_group = aws_rds.CfnDBClusterParameterGroup(
            self,
            "DBClusterParameterGroup",
            description="test",
            family="aurora5.6",
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
        db_secret = None
        db_snapshot_identifier = None
        db_username = None
        db_password = None
        db_snapshot_arn = DB_SNAPSHOT
        db_snapshot_param = core.CfnParameter(
            self,
            "DBSnapshotIdentifier",
            default=db_snapshot_arn
        )
        if db_snapshot_arn:
            db_snapshot_identifier = db_snapshot_param.value_as_string
        else:
            db_secret = aws_secretsmanager.Secret(
                self,
                "secret",
                generate_secret_string=aws_secretsmanager.SecretStringGenerator(
                    exclude_characters="\"@/\\\"'$,[]*?{}~\#%<>|^",
                    exclude_punctuation=True,
                    generate_string_key="password",
                    secret_string_template=json.dumps({"username":"dbadmin"})
                )
            )
            db_username = db_secret.secret_value_from_json("username").to_string()
            db_password = db_secret.secret_value_from_json("password").to_string()
        db_cluster = aws_rds.CfnDBCluster(
            self,
            "DBCluster",
            engine="aurora",
            db_cluster_parameter_group_name=db_cluster_parameter_group.ref,
            db_subnet_group_name=db_subnet_group.ref,
            engine_mode="serverless",
            master_username=db_username,
            master_user_password=db_password,
            scaling_configuration={
                "auto_pause": True,
                "min_capacity": 1,
                "max_capacity": 2,
                "seconds_until_auto_pause": 30
            },
            snapshot_identifier=db_snapshot_identifier,
            storage_encrypted=True,
            vpc_security_group_ids=[ db_sg.security_group_id ]
        )
        alb_sg = aws_ec2.SecurityGroup(
            self,
            "AlbSg",
            vpc=vpc
        )
        alb = aws_elasticloadbalancingv2.ApplicationLoadBalancer(
            self,
            "AppAlb",
            internet_facing=True,
            security_group=alb_sg,
            vpc=vpc
        )
        # if there is no cert...
        http_target_group = aws_elasticloadbalancingv2.ApplicationTargetGroup(
            self,
            "AsgHttpTargetGroup",
            target_type=aws_elasticloadbalancingv2.TargetType.INSTANCE,
            port=80,
            vpc=vpc
        )
        http_target_group.node.default_child.cfn_options.condition = certificate_arn_does_not_exist_condition
        http_listener = aws_elasticloadbalancingv2.ApplicationListener(
            self,
            "HttpListener",
            default_target_groups=[http_target_group],
            load_balancer=alb,
            open=True,
            port=80
        )
        http_listener.node.default_child.cfn_options.condition = certificate_arn_does_not_exist_condition

        # if there is a cert...
        http_redirect_listener = aws_elasticloadbalancingv2.ApplicationListener(
            self,
            "HttpRedirectListener",
            load_balancer=alb,
            open=True,
            port=80
        )
        http_redirect_listener.add_redirect_response(
            "HttpRedirectResponse",
            host="#{host}",
            path="/#{path}",
            port="443",
            protocol="HTTPS",
            query="#{query}",
            status_code="HTTP_301"
        )
        http_redirect_listener.node.default_child.cfn_options.condition = certificate_arn_exists_condition
        https_target_group = aws_elasticloadbalancingv2.ApplicationTargetGroup(
            self,
            "AsgHttpsTargetGroup",
            target_type=aws_elasticloadbalancingv2.TargetType.INSTANCE,
            port=443,
            vpc=vpc
        )
        https_target_group.node.default_child.cfn_options.condition = certificate_arn_exists_condition
        https_listener = aws_elasticloadbalancingv2.ApplicationListener(
            self,
            "HttpsListener",
            certificates=[aws_elasticloadbalancingv2.ListenerCertificate(certificate_arn_param.value_as_string)],
            default_target_groups=[https_target_group],
            load_balancer=alb,
            open=True,
            port=443
        )
        https_listener.node.default_child.cfn_options.condition = certificate_arn_exists_condition

        notification_topic = aws_sns.Topic(
            self,
            "NotificationTopic"
        )
        system_log_group = aws_logs.CfnLogGroup(
            self,
            "DrupalSystemLogGroup",
            retention_in_days=TWO_YEARS_IN_DAYS
        )
        system_log_group.cfn_options.update_replace_policy = core.CfnDeletionPolicy.RETAIN
        system_log_group.cfn_options.deletion_policy = core.CfnDeletionPolicy.RETAIN
        access_log_group = aws_logs.CfnLogGroup(
            self,
            "DrupalAccessLogGroup",
            retention_in_days=TWO_YEARS_IN_DAYS
        )
        access_log_group.cfn_options.update_replace_policy = core.CfnDeletionPolicy.RETAIN
        access_log_group.cfn_options.deletion_policy = core.CfnDeletionPolicy.RETAIN
        error_log_group = aws_logs.CfnLogGroup(
            self,
            "DrupalErrorLogGroup",
            retention_in_days=TWO_YEARS_IN_DAYS
        )
        error_log_group.cfn_options.update_replace_policy = core.CfnDeletionPolicy.RETAIN
        error_log_group.cfn_options.deletion_policy = core.CfnDeletionPolicy.RETAIN
        app_instance_role = aws_iam.Role(
            self,
            "AppInstanceRole",
            assumed_by=aws_iam.ServicePrincipal('ec2.amazonaws.com'),
            inline_policies={
                "AllowStreamLogsToCloudWatch": aws_iam.PolicyDocument(
                    statements=[
                        aws_iam.PolicyStatement(
                            effect=aws_iam.Effect.ALLOW,
                            actions=[
                                'logs:CreateLogStream',
                                'logs:DescribeLogStreams',
                                'logs:PutLogEvents'
                            ],
                            resources=[
                                access_log_group.attr_arn,
                                error_log_group.attr_arn,
                                system_log_group.attr_arn
                            ]
                        )
                    ]
                ),
                "AllowStreamMetricsToCloudWatch": aws_iam.PolicyDocument(
                    statements=[
                        aws_iam.PolicyStatement(
                            effect=aws_iam.Effect.ALLOW,
                            actions=[
                                'ec2:DescribeVolumes',
                                'ec2:DescribeTags',
                                'cloudwatch:GetMetricStatistics',
                                'cloudwatch:ListMetrics',
                                'cloudwatch:PutMetricData'
                            ],
                            resources=['*']
                        )
                    ]
                ),
                "AllowGetFromArtifactBucket": aws_iam.PolicyDocument(
                    statements=[
                        aws_iam.PolicyStatement(
                            effect=aws_iam.Effect.ALLOW,
                            actions=[
                                's3:Get*',
                                's3:Head*'
                            ],
                            resources=[
                                "arn:{}:s3:::{}/*".format(
                                    core.Aws.PARTITION,
                                    artifact_bucket.bucket_name
                                )
                            ]
                        )
                    ]
                )
            }
        )
        app_instance_role.add_managed_policy(aws_iam.ManagedPolicy.from_aws_managed_policy_name('AmazonSSMManagedInstanceCore'));
        instance_profile = aws_iam.CfnInstanceProfile(
            self,
            "AppInstanceProfile",
            roles=[app_instance_role.role_name]
        )
        with open('drupal/scripts/app_launch_config_user_data.sh') as f:
            app_launch_config_user_data = f.read()
        launch_config = aws_autoscaling.CfnLaunchConfiguration(
            self,
            "AppLaunchConfig",
            image_id=AMI, # TODO: Put into CFN Mapping
            instance_type="t3.micro", # TODO: Parameterize
            iam_instance_profile=instance_profile.ref,
            security_groups=[app_sg.security_group_name],
            user_data=(
                core.Fn.base64(
                    core.Fn.sub(app_launch_config_user_data)
                )
            )
        )
        asg = aws_autoscaling.CfnAutoScalingGroup(
            self,
            "AppAsg",
            launch_configuration_name=launch_config.ref,
            # TODO: Parameterize desired_capacity, max_size, min_size
            desired_capacity="1",
            max_size="2",
            min_size="1",
            vpc_zone_identifier=vpc.select_subnets(subnet_type=aws_ec2.SubnetType.PRIVATE).subnet_ids
        )
        # https://github.com/aws/aws-cdk/issues/3615
        asg.add_override(
            "Properties.TargetGroupARNs",
            {
                "Fn::If": [
                    certificate_arn_exists_condition.logical_id,
                    [https_target_group.target_group_arn],
                    [http_target_group.target_group_arn]
                ]
            }
        )
        core.Tag.add(asg, "Name", "{}/AppAsg".format(core.Aws.STACK_NAME))
        asg.add_override("UpdatePolicy.AutoScalingScheduledAction.IgnoreUnmodifiedGroupSizeProperties", True)
        asg.add_override("UpdatePolicy.AutoScalingRollingUpdate.MinInstancesInService", 1)
        asg.add_override("UpdatePolicy.AutoScalingRollingUpdate.WaitOnResourceSignals", True)
        asg.add_override("UpdatePolicy.AutoScalingRollingUpdate.PauseTime", "PT15M")
        asg.add_override("CreationPolicy.ResourceSignal.Count", 1)
        asg.add_override("CreationPolicy.ResourceSignal.Timeout", "PT15M")

        sg_http_ingress = aws_ec2.CfnSecurityGroupIngress(
            self,
            "AppSgHttpIngress",
            from_port=80,
            group_id=app_sg.security_group_id,
            ip_protocol="tcp",
            source_security_group_id=alb_sg.security_group_id,
            to_port=80
        )
        sg_http_ingress.cfn_options.condition = certificate_arn_does_not_exist_condition

        sg_https_ingress = aws_ec2.CfnSecurityGroupIngress(
            self,
            "AppSgHttpsIngress",
            from_port=443,
            group_id=app_sg.security_group_id,
            ip_protocol="tcp",
            source_security_group_id=alb_sg.security_group_id,
            to_port=443
        )
        sg_https_ingress.cfn_options.condition = certificate_arn_exists_condition

        # CICD Pipeline

        # TODO: Tighten role / use managed roles?
        pipeline_role = aws_iam.Role(
            self,
            "PipelineRole",
            assumed_by=aws_iam.ServicePrincipal('codepipeline.amazonaws.com'),
            inline_policies={
                "CodePipelinePerms": aws_iam.PolicyDocument(
                    statements=[
                        aws_iam.PolicyStatement(
                            effect=aws_iam.Effect.ALLOW,
                            actions=[
                                'codedeploy:GetApplication',
                                'codedeploy:GetDeploymentGroup',
                                'codedeploy:ListApplications',
                                'codedeploy:ListDeploymentGroups',
                                'codepipeline:*',
                                'iam:ListRoles',
                                'iam:PassRole',
                                'lambda:GetFunctionConfiguration',
                                'lambda:ListFunctions',
                                's3:CreateBucket',
                                's3:GetBucketPolicy',
                                's3:GetObject',
                                's3:ListAllMyBuckets',
                                's3:ListBucket',
                                's3:PutBucketPolicy'
                            ],
                            resources=['*']
                        )
                    ]
                )
            }
        )

        source_stage_role = aws_iam.Role(
            self,
            "SourceStageRole",
            assumed_by=aws_iam.ArnPrincipal(pipeline_role.role_arn),
            inline_policies={
                "SourceRolePerms": aws_iam.PolicyDocument(
                    statements=[
                        aws_iam.PolicyStatement(
                            effect=aws_iam.Effect.ALLOW,
                            actions=[
                                's3:Get*',
                                's3:Head*'
                            ],
                            resources=[
                                "arn:{}:s3:::{}/{}".format(
                                    core.Aws.PARTITION,
                                    source_artifact_s3_bucket_param.value.to_string(),
                                    source_artifact_s3_object_key_param.value.to_string()
                                )
                            ]
                        ),
                        aws_iam.PolicyStatement(
                            effect=aws_iam.Effect.ALLOW,
                            actions=[
                                's3:GetBucketVersioning'
                            ],
                            resources=[
                                "arn:{}:s3:::{}".format(
                                    core.Aws.PARTITION,
                                    source_artifact_s3_bucket_param.value.to_string()
                                )
                            ]
                        ),
                        aws_iam.PolicyStatement(
                            effect=aws_iam.Effect.ALLOW,
                            actions=[
                                's3:*'
                            ],
                            resources=[
                                "arn:{}:s3:::{}/*".format(
                                    core.Aws.PARTITION,
                                    artifact_bucket.bucket_name
                                )
                            ]
                        )
                    ]
                )
            }
        )

        deploy_stage_role = aws_iam.Role(
            self,
            "DeployStageRole",
            assumed_by=aws_iam.ArnPrincipal(pipeline_role.role_arn),
            inline_policies={
                "DeployRolePerms": aws_iam.PolicyDocument(
                    statements=[
                        aws_iam.PolicyStatement(
                            effect=aws_iam.Effect.ALLOW,
                            actions=[
                                'codedeploy:*'
                            ],
                            resources=['*']
                        ),
                        aws_iam.PolicyStatement(
                            effect=aws_iam.Effect.ALLOW,
                            actions=[
                                's3:Get*',
                                's3:Head*'
                            ],
                            resources=[
                                "arn:{}:s3:::{}/*".format(
                                    core.Aws.PARTITION,
                                    artifact_bucket.bucket_name
                                )
                            ]
                        )
                    ]
                )
            }
        )

        code_deploy_application = aws_codedeploy.CfnApplication(
            self,
            "CodeDeployApplication",
            application_name=core.Aws.STACK_NAME,
            compute_platform="Server"
        )

        code_deploy_role = aws_iam.Role(
             self,
            "CodeDeployRole",
            assumed_by=aws_iam.ServicePrincipal('codedeploy.amazonaws.com'),
            managed_policies=[aws_iam.ManagedPolicy.from_aws_managed_policy_name('service-role/AWSCodeDeployRole')]
        )

        code_deploy_deployment_group = aws_codedeploy.CfnDeploymentGroup(
            self,
            "CodeDeployDeploymentGroup",
            application_name=code_deploy_application.application_name,
            auto_scaling_groups=[asg.ref],
            deployment_group_name="{}-app".format(core.Aws.STACK_NAME),
            deployment_config_name=aws_codedeploy.ServerDeploymentConfig.ALL_AT_ONCE.deployment_config_name,
            service_role_arn=code_deploy_role.role_arn
        )

        pipeline = aws_codepipeline.CfnPipeline(
            self,
            "Pipeline",
            artifact_store=aws_codepipeline.CfnPipeline.ArtifactStoreProperty(
                location=artifact_bucket.bucket_name,
                type='S3'
            ),
            role_arn=pipeline_role.role_arn,
            stages=[
                aws_codepipeline.CfnPipeline.StageDeclarationProperty(
                    name="Source",
                    actions=[
                        aws_codepipeline.CfnPipeline.ActionDeclarationProperty(
                            action_type_id=aws_codepipeline.CfnPipeline.ActionTypeIdProperty(
                                category='Source',
                                owner='AWS',
                                provider='S3',
                                version='1'
                            ),
                            configuration={
                                'S3Bucket': source_artifact_s3_bucket_param.value.to_string(),
                                'S3ObjectKey': source_artifact_s3_object_key_param.value.to_string()
                            },
                            output_artifacts=[
                                aws_codepipeline.CfnPipeline.OutputArtifactProperty(
                                    name="build"
                                )
                            ],
                            name="SourceAction",
                            role_arn=source_stage_role.role_arn
                        )
                    ]
                ),
                aws_codepipeline.CfnPipeline.StageDeclarationProperty(
                    name="Deploy",
                    actions=[
                        aws_codepipeline.CfnPipeline.ActionDeclarationProperty(
                            action_type_id=aws_codepipeline.CfnPipeline.ActionTypeIdProperty(
                                category='Deploy',
                                owner='AWS',
                                provider='CodeDeploy',
                                version='1'
                            ),
                            configuration={
                                'ApplicationName': code_deploy_application.ref,
                                'DeploymentGroupName': code_deploy_deployment_group.ref,
                            },
                            input_artifacts=[
                                aws_codepipeline.CfnPipeline.InputArtifactProperty(
                                    name="build"
                                )
                            ],
                            name="DeployAction",
                            role_arn=deploy_stage_role.role_arn
                        )
                    ]
                )
            ]
        )

        # EFS
        efs_sg = aws_ec2.SecurityGroup(
            self,
            "EfsSg",
            vpc=vpc
        )

        efs_sg.add_ingress_rule(
            peer=app_sg,
            connection=aws_ec2.Port.tcp(2049)
        )

        efs = aws_efs.FileSystem(
            self,
            "AppEfs",
            security_group=efs_sg,
            vpc=vpc
        )

        # cloudfront
        cloudfront_certificate_arn_param = core.CfnParameter(
            self,
            "CloudFrontCertificateArn",
            default="",
            description="The ARN from AWS Certificate Manager for the SSL cert used in CloudFront CDN. Must be in us-east region."
        )
        cloudfront_certificate_arn_exists_condition = core.CfnCondition(
            self,
            "CloudFrontCertificateArnExists",
            expression=core.Fn.condition_not(core.Fn.condition_equals(cloudfront_certificate_arn_param.value, ""))
        )
        cloudfront_enable_param = core.CfnParameter(
            self,
            "CloudFrontEnableParam",
            allowed_values=[ "true", "false" ],
            default="true",
            description="Enable CloudFront CDN support."
        )
        cloudfront_enable_condition = core.CfnCondition(
            self,
            "CloudFrontEnableCondition",
            expression=core.Fn.condition_equals(cloudfront_enable_param.value, "true")
        )
        cloudfront_origin_access_policy_param = core.CfnParameter(
            self,
            "CloudFrontOriginAccessPolicyParam",
            allowed_values = [ "http-only", "https-only", "match-viewer" ],
            default="match-viewer",
            description="CloudFront access policy for communicating with content origin."
        )
        cloudfront_price_class_param = core.CfnParameter(
            self,
            "CloudFrontPriceClassParam",
            # possible to use a map to make the values more human readable
            allowed_values = [
                "PriceClass_All",
                "PriceClass_200",
                "PriceClass_100"
            ],
            default="PriceClass_All",
            description="Price class to use for CloudFront CDN."
        )
        cloudfront_distribution = aws_cloudfront.CfnDistribution(
            self,
            "CloudFrontDistribution",
            distribution_config=aws_cloudfront.CfnDistribution.DistributionConfigProperty(
                # TODO: parameterize or integrate alias with Route53; also requires a valid certificate
                # aliases=[ "{}.dev.patterns.ordinaryexperts.com".format(core.Aws.STACK_NAME) ],
                comment=core.Aws.STACK_NAME,
                default_cache_behavior=aws_cloudfront.CfnDistribution.DefaultCacheBehaviorProperty(
                    allowed_methods=[ "HEAD", "GET" ],
                    compress=False,
                    default_ttl=86400,
                    forwarded_values=aws_cloudfront.CfnDistribution.ForwardedValuesProperty(
                        query_string=False
                    ),
                    min_ttl=0,
                    max_ttl=31536000,
                    target_origin_id="alb",
                    viewer_protocol_policy="allow-all"
                ),
                enabled=True,
                origins=[ aws_cloudfront.CfnDistribution.OriginProperty(
                    domain_name=alb.load_balancer_dns_name,
                    id="alb",
                    custom_origin_config=aws_cloudfront.CfnDistribution.CustomOriginConfigProperty(
                        origin_protocol_policy=cloudfront_origin_access_policy_param.value_as_string
                    )
                )],
                price_class=cloudfront_price_class_param.value_as_string,
                viewer_certificate=aws_cloudfront.CfnDistribution.ViewerCertificateProperty(
                    acm_certificate_arn=core.Fn.condition_if(
                        cloudfront_certificate_arn_exists_condition.logical_id,
                        cloudfront_certificate_arn_param.value_as_string,
                        core.Aws.NO_VALUE
                    ).to_string(),
                    ssl_support_method=core.Fn.condition_if(
                        cloudfront_certificate_arn_exists_condition.logical_id,
                        "sni-only",
                        core.Aws.NO_VALUE
                    ).to_string()
                )
            )
        )
        cloudfront_distribution.add_override(
            "Properties.DistributionConfig.ViewerCertificate.CloudFrontDefaultCertificate",
            {
                "Fn::If": [
                    cloudfront_certificate_arn_exists_condition.logical_id,
                    { "Ref": "AWS::NoValue" },
                    True
                ]
            }
        )
        cloudfront_distribution.cfn_options.condition = cloudfront_enable_condition
        cloudfront_distribution_endpoint_output = core.CfnOutput(
            self,
            "CloudFrontDistributionEndpointOutput",
            condition=cloudfront_enable_condition,
            description="The distribution DNS name endpoint for connection. Configure in Drupal's settings.php.",
            value=cloudfront_distribution.attr_domain_name
        )
        # elasticache
        elasticache_cluster_cache_node_type_param = core.CfnParameter(
            self,
            "ElastiCacheClusterCacheNodeTypeParam",
            allowed_values=[ "cache.m5.large", "cache.m5.xlarge", "cache.m5.2xlarge", "cache.m5.4xlarge", "cache.m5.12xlarge", "cache.m5.24xlarge", "cache.m4.large", "cache.m4.xlarge", "cache.m4.2xlarge", "cache.m4.4xlarge", "cache.m4.10xlarge", "cache.t3.micro", "cache.t3.small", "cache.t3.medium", "cache.t2.micro", "cache.t2.small", "cache.t2.medium" ],
            default="cache.t2.micro",
            type="String"
        )
        elasticache_cluster_engine_version_param = core.CfnParameter(
            self,
            "ElastiCacheClusterEngineVersionParam",
            # TODO: determine which versions are supported by the Drupal memcached module
            allowed_values=[ "1.4.14", "1.4.24", "1.4.33", "1.4.34", "1.4.5", "1.5.10", "1.5.16" ],
            default="1.5.16",
            description="The memcached version of the cache cluster.",
            type="String"
        )
        elasticache_cluster_num_cache_nodes_param = core.CfnParameter(
            self,
            "ElastiCacheClusterNumCacheNodesParam",
            default=2,
            description="The number of cache nodes in the memcached cluster.",
            min_value=1,
            max_value=20,
            type="Number"
        )
        elasticache_enable_param = core.CfnParameter(
            self,
            "ElastiCacheEnableParam",
            allowed_values=[ "true", "false" ],
            default="true",
        )
        elasticache_enable_condition = core.CfnCondition(
            self,
            "ElastiCacheEnableCondition",
            expression=core.Fn.condition_equals(elasticache_enable_param.value, "true")
        )
        elasticache_sg = aws_ec2.SecurityGroup(
            self,
            "ElastiCacheSg",
            vpc=vpc
        )
        elasticache_sg.add_ingress_rule(
            peer=app_sg,
            connection=aws_ec2.Port.tcp(11211)
        )
        elasticache_subnet_group = aws_elasticache.CfnSubnetGroup(
            self,
            "ElastiCacheSubnetGroup",
            description="ElastiCache subnet group",
            subnet_ids=vpc.select_subnets(subnet_type=aws_ec2.SubnetType.PRIVATE).subnet_ids
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
            vpc_security_group_ids=[ elasticache_sg.security_group_id ]
        )
        core.Tag.add(asg, "oe:patterns:drupal:stack", core.Aws.STACK_NAME)
        elasticache_cluster.cfn_options.condition = elasticache_enable_condition
        elasticache_cluster_id_output = core.CfnOutput(
            self,
            "ElastiCacheClusterIdOutput",
            condition=elasticache_enable_condition,
            description="The Id of the ElastiCache cluster.",
            value=elasticache_cluster.ref
        )
        elasticache_cluster_endpoint_output = core.CfnOutput(
            self,
            "ElastiCacheClusterEndpointOutput",
            condition=elasticache_enable_condition,
            description="The endpoint of the cluster for connection. Configure in Drupal's settings.php.",
            value="{}:{}".format(elasticache_cluster.attr_configuration_endpoint_address,
                                 elasticache_cluster.attr_configuration_endpoint_port)
        )
