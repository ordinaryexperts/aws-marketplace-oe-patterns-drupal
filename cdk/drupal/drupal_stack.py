import json
from aws_cdk import (
    aws_autoscaling, aws_ec2, aws_elasticloadbalancingv2, aws_iam,
    aws_logs, aws_rds, aws_secretsmanager, aws_sns, core
)

AMI="ami-0423ff58236b36794"
TWO_YEARS_IN_DAYS=731

class DrupalStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

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
            "vpc",
            cidr="10.0.0.0/16"
        )
        secret = aws_secretsmanager.Secret(
            self,
            "secret",
            generate_secret_string=aws_secretsmanager.SecretStringGenerator(
                secret_string_template=json.dumps({"username":"user"}),
                generate_string_key="password"
            )
        )
        rds_sg = aws_ec2.SecurityGroup(
            self,
            "RdsSg",
            vpc=vpc,
            allow_all_outbound=False
        )
        rds_sg.add_ingress_rule(aws_ec2.Peer.ipv4(vpc.vpc_cidr_block), aws_ec2.Port.tcp(3306))
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
        db_cluster = aws_rds.CfnDBCluster(
            self,
            "DBCluster",
            engine="aurora",
            db_cluster_parameter_group_name=db_cluster_parameter_group.ref,
            db_subnet_group_name=db_subnet_group.ref,
            engine_mode="serverless",
            master_username="dbadmin",
            # TODO: get this working
            # https://docs.aws.amazon.com/cdk/latest/guide/get_secrets_manager_value.html
            # master_user_password=core.SecretValue.cfnDynamicReference(secret),
            master_user_password="dbpassword",
            scaling_configuration={
                "auto_pause": True,
                "min_capacity": 1,
                "max_capacity": 2,
                "seconds_until_auto_pause": 30
            },
            storage_encrypted=True,
            vpc_security_group_ids=[ rds_sg.security_group_id ]
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
                "AllowGetFromGithubArtifactBucket": aws_iam.PolicyDocument(
                    statements=[
                        aws_iam.PolicyStatement(
                            effect=aws_iam.Effect.ALLOW,
                            actions=[
                                's3:GetObject',
                            ],
                            resources=['arn:aws:s3:::github-user-and-bucket-githubartifactbucket-1c9jk3sjkqv8p/*']
                        )
                    ]
                )
            }
        )
        app_instance_role.add_managed_policy(aws_iam.ManagedPolicy.from_aws_managed_policy_name('AmazonSSMManagedInstanceCore'));
        sg = aws_ec2.SecurityGroup(
            self,
            "AppSg",
            vpc=vpc
        )
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
            security_groups=[sg.security_group_id],
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
            max_size="1",
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
        core.Tag.add(asg, "Name", "{}/AppAsg".format(self.stack_name))
        asg.add_override("UpdatePolicy.AutoScalingScheduledAction.IgnoreUnmodifiedGroupSizeProperties", True)

        sg_http_ingress = aws_ec2.CfnSecurityGroupIngress(
            self,
            "AppSgHttpIngress",
            from_port=80,
            group_id=sg.security_group_id,
            ip_protocol="tcp",
            source_security_group_id=alb_sg.security_group_id,
            to_port=80
        )
        sg_http_ingress.cfn_options.condition = certificate_arn_does_not_exist_condition

        sg_https_ingress = aws_ec2.CfnSecurityGroupIngress(
            self,
            "AppSgHttpsIngress",
            from_port=443,
            group_id=sg.security_group_id,
            ip_protocol="tcp",
            source_security_group_id=alb_sg.security_group_id,
            to_port=443
        )
        sg_https_ingress.cfn_options.condition = certificate_arn_exists_condition
