import json
from aws_cdk import (
    aws_autoscaling,
    aws_cloudfront,
    aws_cloudwatch,
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
    aws_ssm,
    core
)

AMI="ami-0ca74418ad03a79c8"
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
            default="github-user-and-bucket-githubartifactbucket-wl52dae3lyub"
        )
        source_artifact_s3_object_key_param = core.CfnParameter(
            self,
            "SourceArtifactS3ObjectKey",
            default="aws-marketplace-oe-patterns-drupal-example-site/refs/heads/feature/DP-68--secrets-management-and-database-init.tar.gz"
        )
        notification_email_param = core.CfnParameter(
            self,
            "NotificationEmail",
            default=""
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
        notification_email_exists_condition = core.CfnCondition(
            self,
            "NotificationEmailExists",
            expression=core.Fn.condition_not(core.Fn.condition_equals(notification_email_param.value, ""))
        )

        # VPC
        customer_vpc_id_param = core.CfnParameter(
            self,
            "CustomerVpcId",
            default=""
        )
        customer_vpc_public_subnet_id1 = core.CfnParameter(
            self,
            "CustomerVpcPublicSubnet1",
            default=""
        )
        customer_vpc_public_subnet_id2 = core.CfnParameter(
            self,
            "CustomerVpcPublicSubnet2",
            default=""
        )
        customer_vpc_private_subnet_id1 = core.CfnParameter(
            self,
            "CustomerVpcPrivateSubnet1",
            default=""
        )
        customer_vpc_private_subnet_id2 = core.CfnParameter(
            self,
            "CustomerVpcPrivateSubnet2",
            default=""
        )
        customer_vpc_given_condition = core.CfnCondition(
            self,
            "CustomerVpcGiven",
            expression=core.Fn.condition_not(core.Fn.condition_equals(customer_vpc_id_param.value, ""))
        )
        customer_vpc_not_given_condition = core.CfnCondition(
            self,
            "CustomerVpcNotGiven",
            expression=core.Fn.condition_equals(customer_vpc_id_param.value, "")
        )
        vpc = aws_ec2.CfnVPC(
            self,
            "Vpc",
            cidr_block="10.0.0.0/16",
            enable_dns_hostnames=True,
            enable_dns_support=True,
            instance_tenancy="default",
            tags=[core.CfnTag(key="Name", value="{}/Vpc".format(core.Aws.STACK_NAME))]
        )
        vpc.cfn_options.condition=customer_vpc_not_given_condition

        vpc_igw = aws_ec2.CfnInternetGateway(
            self,
            "VpcInternetGateway",
            tags=[core.CfnTag(key="Name", value="{}/Vpc".format(core.Aws.STACK_NAME))]
        )
        vpc_igw.cfn_options.condition=customer_vpc_not_given_condition
        vpc_igw_attachment = aws_ec2.CfnVPCGatewayAttachment(
            self,
            "VpcIGWAttachment",
            vpc_id=vpc.ref,
            internet_gateway_id=vpc_igw.ref
        )
        vpc_igw_attachment.cfn_options.condition=customer_vpc_not_given_condition

        vpc_public_route_table = aws_ec2.CfnRouteTable(
            self,
            "VpcPublicRouteTable",
            vpc_id=vpc.ref,
            tags=[core.CfnTag(key="Name", value="{}/Vpc/PublicRouteTable".format(core.Aws.STACK_NAME))]
        )
        vpc_public_route_table.cfn_options.condition=customer_vpc_not_given_condition
        vpc_public_default_route = aws_ec2.CfnRoute(
            self,
            "VpcPublicDefaultRoute",
            route_table_id=vpc_public_route_table.ref,
            destination_cidr_block="0.0.0.0/0",
            gateway_id=vpc_igw.ref
        )
        vpc_public_default_route.cfn_options.condition=customer_vpc_not_given_condition

        vpc_public_subnet1 = aws_ec2.CfnSubnet(
            self,
            "VpcPublicSubnet1",
            cidr_block="10.0.0.0/18",
            vpc_id=vpc.ref,
            assign_ipv6_address_on_creation=None,
            availability_zone=core.Fn.select(0, core.Fn.get_azs()),
            map_public_ip_on_launch=True,
            tags=[
                core.CfnTag(key="Name", value="{}/Vpc/PublicSubnet1".format(core.Aws.STACK_NAME)),
                core.CfnTag(key="aws-cdk:subnet-name", value="Public"),
                core.CfnTag(key="aws-cdk:subnet-type", value="Public")
            ]
        )
        vpc_public_subnet1.cfn_options.condition=customer_vpc_not_given_condition
        vpc_public_subnet1_route_table_association = aws_ec2.CfnSubnetRouteTableAssociation(
            self,
            "VpcPublicSubnet1RouteTableAssociation",
            route_table_id=vpc_public_route_table.ref,
            subnet_id=vpc_public_subnet1.ref
        )
        vpc_public_subnet1_route_table_association.cfn_options.condition=customer_vpc_not_given_condition
        vpc_public_subnet1_eip = aws_ec2.CfnEIP(
            self,
            "VpcPublicSubnet1EIP",
            domain="vpc"
        )
        vpc_public_subnet1_eip.cfn_options.condition=customer_vpc_not_given_condition
        vpc_public_subnet1_nat_gateway = aws_ec2.CfnNatGateway(
            self,
            "VpcPublicSubnet1NATGateway",
            allocation_id=vpc_public_subnet1_eip.attr_allocation_id,
            subnet_id=vpc_public_subnet1.ref,
            tags=[core.CfnTag(key="Name", value="{}/Vpc/PublicSubnet1".format(core.Aws.STACK_NAME))]
        )
        vpc_public_subnet1_nat_gateway.cfn_options.condition=customer_vpc_not_given_condition

        vpc_public_subnet2 = aws_ec2.CfnSubnet(
            self,
            "VpcPublicSubnet2",
            cidr_block="10.0.64.0/18",
            vpc_id=vpc.ref,
            assign_ipv6_address_on_creation=None,
            availability_zone=core.Fn.select(1, core.Fn.get_azs()),
            map_public_ip_on_launch=True,
            tags=[
                core.CfnTag(key="Name", value="{}/Vpc/PublicSubnet2".format(core.Aws.STACK_NAME)),
                core.CfnTag(key="aws-cdk:subnet-name", value="Public"),
                core.CfnTag(key="aws-cdk:subnet-type", value="Public")
            ]
        )
        vpc_public_subnet2.cfn_options.condition=customer_vpc_not_given_condition
        vpc_public_subnet2_route_table_association = aws_ec2.CfnSubnetRouteTableAssociation(
            self,
            "VpcPublicSubnet2RouteTableAssociation",
            route_table_id=vpc_public_route_table.ref,
            subnet_id=vpc_public_subnet2.ref
        )
        vpc_public_subnet2_route_table_association.cfn_options.condition=customer_vpc_not_given_condition
        vpc_public_subnet2_eip = aws_ec2.CfnEIP(
            self,
            "VpcPublicSubnet2EIP",
            domain="vpc"
        )
        vpc_public_subnet2_eip.cfn_options.condition=customer_vpc_not_given_condition
        vpc_public_subnet2_nat_gateway = aws_ec2.CfnNatGateway(
            self,
            "VpcPublicSubnet2NATGateway",
            allocation_id=vpc_public_subnet2_eip.attr_allocation_id,
            subnet_id=vpc_public_subnet1.ref,
            tags=[core.CfnTag(key="Name", value="{}/Vpc/PublicSubnet2".format(core.Aws.STACK_NAME))]
        )
        vpc_public_subnet2_nat_gateway.cfn_options.condition=customer_vpc_not_given_condition

        vpc_private_subnet1 = aws_ec2.CfnSubnet(
            self,
            "VpcPrivateSubnet1",
            cidr_block="10.0.128.0/18",
            vpc_id=vpc.ref,
            assign_ipv6_address_on_creation=None,
            availability_zone=core.Fn.select(0, core.Fn.get_azs()),
            map_public_ip_on_launch=False,
            tags=[
                core.CfnTag(key="Name", value="{}/Vpc/PrivateSubnet1".format(core.Aws.STACK_NAME)),
                core.CfnTag(key="aws-cdk:subnet-name", value="Private"),
                core.CfnTag(key="aws-cdk:subnet-type", value="Private")
            ]
        )
        vpc_private_subnet1.cfn_options.condition=customer_vpc_not_given_condition
        vpc_private_subnet1_route_table = aws_ec2.CfnRouteTable(
            self,
            "VpcPrivateSubnet1RouteTable",
            vpc_id=vpc.ref,
            tags=[core.CfnTag(key="Name", value="{}/Vpc/PrivateSubnet1".format(core.Aws.STACK_NAME))]
        )
        vpc_private_subnet1_route_table.cfn_options.condition=customer_vpc_not_given_condition
        vpc_private_subnet1_route_table_association = aws_ec2.CfnSubnetRouteTableAssociation(
            self,
            "VpcPrivateSubnet1RouteTableAssociation",
            route_table_id=vpc_private_subnet1_route_table.ref,
            subnet_id=vpc_private_subnet1.ref
        )
        vpc_private_subnet1_route_table_association.cfn_options.condition=customer_vpc_not_given_condition
        vpc_private_subnet1_default_route = aws_ec2.CfnRoute(
            self,
            "VpcPrivateSubnet1DefaultRoute",
            route_table_id=vpc_private_subnet1_route_table.ref,
            destination_cidr_block="0.0.0.0/0",
            nat_gateway_id=vpc_public_subnet1_nat_gateway.ref
        )
        vpc_private_subnet1_default_route.cfn_options.condition=customer_vpc_not_given_condition

        vpc_private_subnet2 = aws_ec2.CfnSubnet(
            self,
            "VpcPrivateSubnet2",
            cidr_block="10.0.192.0/18",
            vpc_id=vpc.ref,
            assign_ipv6_address_on_creation=None,
            availability_zone=core.Fn.select(1, core.Fn.get_azs()),
            map_public_ip_on_launch=False,
            tags=[
                core.CfnTag(key="Name", value="{}/Vpc/PrivateSubnet2".format(core.Aws.STACK_NAME)),
                core.CfnTag(key="aws-cdk:subnet-name", value="Private"),
                core.CfnTag(key="aws-cdk:subnet-type", value="Private")
            ]
        )
        vpc_private_subnet2.cfn_options.condition=customer_vpc_not_given_condition
        vpc_private_subnet2_route_table = aws_ec2.CfnRouteTable(
            self,
            "VpcPrivateSubnet2RouteTable",
            vpc_id=vpc.ref,
            tags=[core.CfnTag(key="Name", value="{}/Vpc/PrivateSubnet2".format(core.Aws.STACK_NAME))]
        )
        vpc_private_subnet2_route_table.cfn_options.condition=customer_vpc_not_given_condition
        vpc_private_subnet2_route_table_association = aws_ec2.CfnSubnetRouteTableAssociation(
            self,
            "VpcPrivateSubnet2RouteTableAssociation",
            route_table_id=vpc_private_subnet2_route_table.ref,
            subnet_id=vpc_private_subnet2.ref
        )
        vpc_private_subnet2_route_table_association.cfn_options.condition=customer_vpc_not_given_condition
        vpc_private_subnet2_default_route = aws_ec2.CfnRoute(
            self,
            "VpcPrivateSubnet2DefaultRoute",
            route_table_id=vpc_private_subnet2_route_table.ref,
            destination_cidr_block="0.0.0.0/0",
            nat_gateway_id=vpc_public_subnet2_nat_gateway.ref
        )
        vpc_private_subnet2_default_route.cfn_options.condition=customer_vpc_not_given_condition

        app_sg = aws_ec2.CfnSecurityGroup(
            self,
            "AppSg",
            group_description="App SG"
        )
        app_sg.add_override(
            "Properties.VpcId",
            {
                "Fn::If": [
                    customer_vpc_not_given_condition.logical_id,
                    vpc.ref,
                    customer_vpc_id_param.value.to_string()
                ]
            }
        )
        db_sg = aws_ec2.CfnSecurityGroup(
            self,
            "DBSg",
            group_description="Database SG"
        )
        db_sg.add_override(
            "Properties.VpcId",
            {
                "Fn::If": [
                    customer_vpc_not_given_condition.logical_id,
                    vpc.ref,
                    customer_vpc_id_param.value.to_string()
                ]
            }
        )
        db_sg_ingress = aws_ec2.CfnSecurityGroupIngress(
            self,
            "DBSgIngress",
            from_port=3306,
            group_id=db_sg.ref,
            ip_protocol="tcp",
            source_security_group_id=app_sg.ref,
            to_port=3306
        )
        db_subnet_group = core.CfnResource(
            self,
            "DBSubnetGroup",
            type="AWS::RDS::DBSubnetGroup",
            properties={
                "DBSubnetGroupDescription": "MySQL Aurora DB Subnet Group",
                "SubnetIds":  {
                    "Fn::If": [
                        customer_vpc_not_given_condition.logical_id,
                        [
                            vpc_private_subnet1.ref,
                            vpc_private_subnet2.ref
                        ],
                        [
                            customer_vpc_private_subnet_id1.value.to_string(),
                            customer_vpc_private_subnet_id2.value.to_string()
                            
                        ]
                    ]
                }
            }
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
        db_snapshot_identifier_param = core.CfnParameter(
            self,
            "DBSnapshotIdentifier",
            default="",
            description="An RDS database cluster snapshot ARN from which to restore. If this parameter is specified, you MUST manually edit the secret values to specify the snapshot credentials for the application."
        )
        db_snapshot_identifier_exists_condition = core.CfnCondition(
            self,
            "DBSnapshotIdentifierExistsCondition",
            expression=core.Fn.condition_not(core.Fn.condition_equals(db_snapshot_identifier_param.value, ""))
        )
        db_secret_arn_param = core.CfnParameter(
            self,
            "DBSecretArn",
            default="",
            description="The ARN of an existing SecretsManager secret used to access the database credentials and store other configuration.",
            type="String"
        )
        db_secret_arn_exists_condition = core.CfnCondition(
            self,
            "DBSecretArnExistsCondition",
            expression=core.Fn.condition_not(core.Fn.condition_equals(db_secret_arn_param.value, ""))
        )
        db_secret_arn_not_exists_condition = core.CfnCondition(
            self,
            "DBSecretArnNotExistsCondition",
            expression=core.Fn.condition_equals(db_secret_arn_param.value, "")
        )
        db_secret = aws_secretsmanager.CfnSecret(
            self,
            "DBSecret",
            generate_secret_string=aws_secretsmanager.CfnSecret.GenerateSecretStringProperty(
                exclude_characters="\"@/\\\"'$,[]*?{}~\#%<>|^",
                exclude_punctuation=True,
                generate_string_key="password",
                secret_string_template=json.dumps({"username":"dbadmin"})
            ),
            # TODO: add encryption key
            # kms_key_id="",
            name="{}/drupal/secret".format(core.Aws.STACK_NAME)
        )
        db_secret_policy = aws_iam.Policy(
            self,
            "DBSecretPolicy",
            statements=[
                aws_iam.PolicyStatement(
                    effect=aws_iam.Effect.ALLOW,
                    actions=[
                        "secretsmanager:GetSecretValue"
                    ],
                    resources=[
                        db_secret.ref,
                        core.Fn.condition_if(
                            db_secret_arn_exists_condition.logical_id,
                            db_secret_arn_param.value_as_string,
                            core.Aws.NO_VALUE
                        ).to_string()
                    ]
                ),
                aws_iam.PolicyStatement(
                    effect=aws_iam.Effect.ALLOW,
                    actions=[ "secretsmanager:ListSecrets" ],
                    resources=[ "*" ],
                ),
            ]
        )
        # TODO: unable to get conditional secret working because the DBCluster username and password depend on the
        # interpolated value in the Fn.condition_if statements; possibly create a nested secret stack and create the
        # secret if it receives a blank param; returning param name in stack output?
        # secret.cfn_options.condition = secret_arn_not_exists_condition

        db_cluster = aws_rds.CfnDBCluster(
            self,
            "DBCluster",
            engine="aurora",
            db_cluster_parameter_group_name=db_cluster_parameter_group.ref,
            db_subnet_group_name=db_subnet_group.ref,
            engine_mode="serverless",
            master_username=core.Fn.condition_if(
                db_snapshot_identifier_exists_condition.logical_id,
                core.Aws.NO_VALUE,
                core.Fn.condition_if(
                    db_secret_arn_exists_condition.logical_id,
                    core.Fn.sub("{{resolve:secretsmanager:${DBSecretArn}:SecretString:username}}"),
                    core.Fn.sub("{{resolve:secretsmanager:${DBSecret}:SecretString:username}}")
                ).to_string(),
            ).to_string(),
            master_user_password=core.Fn.condition_if(
                db_snapshot_identifier_exists_condition.logical_id,
                core.Aws.NO_VALUE,
                core.Fn.condition_if(
                    db_secret_arn_exists_condition.logical_id,
                    core.Fn.sub("{{resolve:secretsmanager:${DBSecretArn}:SecretString:password}}"),
                    core.Fn.sub("{{resolve:secretsmanager:${DBSecret}:SecretString:password}}"),
                ).to_string(),
            ).to_string(),
            scaling_configuration={
                "auto_pause": True,
                "min_capacity": 1,
                "max_capacity": 2,
                "seconds_until_auto_pause": 30
            },
            snapshot_identifier=core.Fn.condition_if(
                db_snapshot_identifier_exists_condition.logical_id,
                db_snapshot_identifier_param.value_as_string,
                core.Aws.NO_VALUE
            ).to_string(),
            storage_encrypted=True,
            vpc_security_group_ids=[ db_sg.ref ]
        )
        alb_sg = aws_ec2.CfnSecurityGroup(
            self,
            "ALBSg",
            group_description="ALB SG"
        )
        alb_sg.add_override(
            "Properties.VpcId",
            {
                "Fn::If": [
                    customer_vpc_not_given_condition.logical_id,
                    vpc.ref,
                    customer_vpc_id_param.value.to_string()
                ]
            }
        )
        alb_http_ingress = aws_ec2.CfnSecurityGroupIngress(
            self,
            "AlbSgHttpIngress",
            cidr_ip="0.0.0.0/0",
            description="Allow from anyone on port 80",
            from_port=80,
            group_id=alb_sg.ref,
            ip_protocol="tcp",
            to_port=80
        )
        alb_https_ingress = aws_ec2.CfnSecurityGroupIngress(
            self,
            "AlbSgHttpsIngress",
            cidr_ip="0.0.0.0/0",
            description="Allow from anyone on port 443",
            from_port=443,
            group_id=alb_sg.ref,
            ip_protocol="tcp",
            to_port=443
        )
        alb = aws_elasticloadbalancingv2.CfnLoadBalancer(
            self,
            "AppAlb",
            scheme="internet-facing",
            security_groups=[ alb_sg.ref ],
            type="application"
        )
        alb.add_override(
            "Properties.Subnets",
            {
                "Fn::If": [
                    customer_vpc_not_given_condition.logical_id,
                    [
                        vpc_public_subnet1.ref,
                        vpc_public_subnet2.ref
                    ],
                    [
                        customer_vpc_public_subnet_id1.value.to_string(),
                        customer_vpc_public_subnet_id2.value.to_string()
                    ]
                ]
            }
        )
        alb_dns_name_output = core.CfnOutput(
            self,
            "AlbDnsNameOutput",
            description="The DNS name of the application load balancer.",
            value=alb.attr_dns_name
        )
        # if there is no cert...
        http_target_group = aws_elasticloadbalancingv2.CfnTargetGroup(
            self,
            "AsgHttpTargetGroup",
            health_check_enabled=None,
            health_check_interval_seconds=None,
            port=80,
            protocol="HTTP",
            target_type="instance"
        )
        http_target_group.add_override(
            "Properties.VpcId",
            {
                "Fn::If": [
                    customer_vpc_not_given_condition.logical_id,
                    vpc.ref,
                    customer_vpc_id_param.value.to_string()
                ]
            }
        )
        http_target_group.cfn_options.condition = certificate_arn_does_not_exist_condition
        http_listener = aws_elasticloadbalancingv2.CfnListener(
            self,
            "HttpListener",
            default_actions=[],
            load_balancer_arn=alb.ref,
            port=80,
            protocol="HTTP"
        )
        http_listener.add_override(
            "Properties.DefaultActions.0.TargetGroupArn", http_target_group.ref
        )
        http_listener.add_override("Properties.DefaultActions.0.Type", "forward")
        http_listener.cfn_options.condition = certificate_arn_does_not_exist_condition

        # if there is a cert...
        http_redirect_listener = aws_elasticloadbalancingv2.CfnListener(
            self,
            "HttpRedirectListener",
            default_actions=[],
            load_balancer_arn=alb.ref,
            port=80,
            protocol="HTTP"
        )
        http_redirect_listener.add_override(
            "Properties.DefaultActions.0.RedirectConfig", 
            {
                "Host": "#{host}",
                "Path": "/#{path}",
                "Port": "443",
                "Protocol": "HTTPS",
                "Query": "#{query}",
                "StatusCode": "HTTP_301"
            }
        )
        http_redirect_listener.add_override("Properties.DefaultActions.0.Type", "redirect")
        http_redirect_listener.cfn_options.condition = certificate_arn_exists_condition
        https_target_group = aws_elasticloadbalancingv2.CfnTargetGroup(
            self,
            "AsgHttpsTargetGroup",
            health_check_enabled=None,
            health_check_interval_seconds=None,
            port=443,
            protocol="HTTPS",
            target_type="instance"
        )
        https_target_group.add_override(
            "Properties.VpcId",
            {
                "Fn::If": [
                    customer_vpc_not_given_condition.logical_id,
                    vpc.ref,
                    customer_vpc_id_param.value.to_string()
                ]
            }
        )
        https_target_group.cfn_options.condition = certificate_arn_exists_condition
        https_listener = aws_elasticloadbalancingv2.CfnListener(
            self,
            "HttpsListener",
            certificates=[],
            default_actions=[],
            load_balancer_arn=alb.ref,
            port=443,
            protocol="HTTPS"
        )
        https_listener.add_override(
            "Properties.DefaultActions.0.TargetGroupArn", https_target_group.ref
        )
        https_listener.add_override(
            "Properties.Certificates.0.CertificateArn", certificate_arn_param.value_as_string
        )
        https_listener.add_override("Properties.DefaultActions.0.Type", "forward")
        https_listener.cfn_options.condition = certificate_arn_exists_condition

        # notifications
        notification_topic = aws_sns.Topic(
            self,
            "NotificationTopic"
        )
        notification_subscription = aws_sns.CfnSubscription(
            self,
            "NotificationSubscription",
            protocol="email",
            topic_arn=notification_topic.topic_arn,
            endpoint=notification_email_param.value_as_string
        )
        notification_subscription.cfn_options.condition = notification_email_exists_condition

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

        # efs
        efs_sg = aws_ec2.CfnSecurityGroup(
            self,
            "EfsSg",
            group_description="EFS SG"
        )
        efs_sg.add_override(
            "Properties.VpcId",
            {
                "Fn::If": [
                    customer_vpc_not_given_condition.logical_id,
                    vpc.ref,
                    customer_vpc_id_param.value.to_string()
                ]
            }
        )
        efs_sg_ingress = aws_ec2.CfnSecurityGroupIngress(
            self,
            "EFSSgIngress",
            from_port=2049,
            group_id=db_sg.ref,
            ip_protocol="tcp",
            source_security_group_id=app_sg.ref,
            to_port=2049
        )
        efs = aws_efs.CfnFileSystem(
            self,
            "AppEfs"
        )
        efs_mount_target1 = aws_efs.CfnMountTarget(
            self,
            "AppEfsMountTarget1",
            file_system_id=efs.ref,
            security_groups=[ efs_sg.ref ],
            subnet_id="" # will be overridden just below
        )
        efs_mount_target1.add_override(
            "Properties.SubnetId",
            {
                "Fn::If": [
                    customer_vpc_not_given_condition.logical_id,
                    vpc_private_subnet1.ref,
                    customer_vpc_private_subnet_id1.value.to_string()
                ]
            }
        )
        efs_mount_target2 = aws_efs.CfnMountTarget(
            self,
            "AppEfsMountTarget2",
            file_system_id=efs.ref,
            security_groups=[ efs_sg.ref ],
            subnet_id="" # will be overridden just below
        )
        efs_mount_target2.add_override(
            "Properties.SubnetId",
            {
                "Fn::If": [
                    customer_vpc_not_given_condition.logical_id,
                    vpc_private_subnet2.ref,
                    customer_vpc_private_subnet_id2.value.to_string()
                ]
            }
        )

        # app
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
        app_instance_role.attach_inline_policy(db_secret_policy)
        instance_profile = aws_iam.CfnInstanceProfile(
            self,
            "AppInstanceProfile",
            roles=[app_instance_role.role_name]
        )

        # autoscaling
        app_instance_type_param = core.CfnParameter(
            self,
            "AppLaunchConfigInstanceType",
            allowed_values=[
                'a1.2xlarge', 'a1.4xlarge', 'a1.large', 'a1.medium', 'a1.metal', 'a1.xlarge', 'c1.medium',
                'c1.xlarge', 'c3.2xlarge', 'c3.4xlarge', 'c3.8xlarge', 'c3.large', 'c3.xlarge', 'c4.2xlarge',
                'c4.4xlarge', 'c4.8xlarge', 'c4.large', 'c4.xlarge', 'c5.12xlarge', 'c5.18xlarge', 'c5.24xlarge',
                'c5.2xlarge', 'c5.4xlarge', 'c5.9xlarge', 'c5.large', 'c5.metal', 'c5.xlarge', 'c5d.12xlarge',
                'c5d.18xlarge', 'c5d.24xlarge', 'c5d.2xlarge', 'c5d.4xlarge', 'c5d.9xlarge', 'c5d.large',
                'c5d.metal', 'c5d.xlarge', 'c5n.18xlarge', 'c5n.2xlarge', 'c5n.4xlarge', 'c5n.9xlarge',
                'c5n.large', 'c5n.metal', 'c5n.xlarge', 'cc2.8xlarge', 'cr1.8xlarge', 'd2.2xlarge', 'd2.4xlarge',
                'd2.8xlarge', 'd2.xlarge', 'f1.16xlarge', 'f1.2xlarge', 'f1.4xlarge', 'g2.2xlarge', 'g2.8xlarge',
                'g3.16xlarge', 'g3.4xlarge', 'g3.8xlarge', 'g3s.xlarge', 'g4dn.12xlarge', 'g4dn.16xlarge',
                'g4dn.2xlarge', 'g4dn.4xlarge', 'g4dn.8xlarge', 'g4dn.metal', 'g4dn.xlarge', 'h1.16xlarge',
                'h1.2xlarge', 'h1.4xlarge', 'h1.8xlarge', 'hs1.8xlarge', 'i2.2xlarge', 'i2.4xlarge',
                'i2.8xlarge', 'i2.xlarge', 'i3.16xlarge', 'i3.2xlarge', 'i3.4xlarge', 'i3.8xlarge', 'i3.large',
                'i3.metal', 'i3.xlarge', 'i3en.12xlarge', 'i3en.24xlarge', 'i3en.2xlarge', 'i3en.3xlarge',
                'i3en.6xlarge', 'i3en.large', 'i3en.metal', 'i3en.xlarge', 'm1.large', 'm1.medium', 'm1.small',
                'm1.xlarge', 'm2.2xlarge', 'm2.4xlarge', 'm2.xlarge', 'm3.2xlarge', 'm3.large', 'm3.medium',
                'm3.xlarge', 'm4.10xlarge', 'm4.16xlarge', 'm4.2xlarge', 'm4.4xlarge', 'm4.large', 'm4.xlarge',
                'm5.12xlarge', 'm5.16xlarge', 'm5.24xlarge', 'm5.2xlarge', 'm5.4xlarge', 'm5.8xlarge', 'm5.large',
                'm5.metal', 'm5.xlarge', 'm5a.12xlarge', 'm5a.16xlarge', 'm5a.24xlarge', 'm5a.2xlarge',
                'm5a.4xlarge', 'm5a.8xlarge', 'm5a.large', 'm5a.xlarge', 'm5ad.12xlarge', 'm5ad.24xlarge',
                'm5ad.2xlarge', 'm5ad.4xlarge', 'm5ad.large', 'm5ad.xlarge', 'm5d.12xlarge', 'm5d.16xlarge',
                'm5d.24xlarge', 'm5d.2xlarge', 'm5d.4xlarge', 'm5d.8xlarge', 'm5d.large', 'm5d.metal', 'm5d.xlarge',
                'm5dn.12xlarge', 'm5dn.16xlarge', 'm5dn.24xlarge', 'm5dn.2xlarge', 'm5dn.4xlarge', 'm5dn.8xlarge',
                'm5dn.large', 'm5dn.metal', 'm5dn.xlarge', 'm5n.12xlarge', 'm5n.16xlarge', 'm5n.24xlarge',
                'm5n.2xlarge', 'm5n.4xlarge', 'm5n.8xlarge', 'm5n.large', 'm5n.metal', 'm5n.xlarge', 'p2.16xlarge',
                'p2.8xlarge', 'p2.xlarge', 'p3.16xlarge', 'p3.2xlarge', 'p3.8xlarge', 'p3dn.24xlarge', 'r3.2xlarge',
                'r3.4xlarge', 'r3.8xlarge', 'r3.large', 'r3.xlarge', 'r4.16xlarge', 'r4.2xlarge', 'r4.4xlarge',
                'r4.8xlarge', 'r4.large', 'r4.xlarge', 'r5.12xlarge', 'r5.16xlarge', 'r5.24xlarge', 'r5.2xlarge',
                'r5.4xlarge', 'r5.8xlarge', 'r5.large', 'r5.metal', 'r5.xlarge', 'r5a.12xlarge', 'r5a.16xlarge',
                'r5a.24xlarge', 'r5a.2xlarge', 'r5a.4xlarge', 'r5a.8xlarge', 'r5a.large', 'r5a.xlarge', 'r5ad.12xlarge',
                'r5ad.24xlarge', 'r5ad.2xlarge', 'r5ad.4xlarge', 'r5ad.large', 'r5ad.xlarge', 'r5d.12xlarge',
                'r5d.16xlarge', 'r5d.24xlarge', 'r5d.2xlarge', 'r5d.4xlarge', 'r5d.8xlarge', 'r5d.large',
                'r5d.metal', 'r5d.xlarge', 'r5dn.12xlarge', 'r5dn.16xlarge', 'r5dn.24xlarge', 'r5dn.2xlarge',
                'r5dn.4xlarge', 'r5dn.8xlarge', 'r5dn.large', 'r5dn.metal', 'r5dn.xlarge', 'r5n.12xlarge',
                'r5n.16xlarge', 'r5n.24xlarge', 'r5n.2xlarge', 'r5n.4xlarge', 'r5n.8xlarge', 'r5n.large',
                'r5n.metal', 'r5n.xlarge', 't1.micro', 't2.2xlarge', 't2.large', 't2.medium', 't2.micro',
                't2.nano', 't2.small', 't2.xlarge', 't3.2xlarge', 't3.large', 't3.medium', 't3.micro',
                't3.nano', 't3.small', 't3.xlarge', 't3a.2xlarge', 't3a.large', 't3a.medium', 't3a.micro',
                't3a.nano', 't3a.small', 't3a.xlarge', 'u-18tb1.metal', 'u-24tb1.metal', 'x1.16xlarge',
                'x1.32xlarge', 'x1e.16xlarge', 'x1e.2xlarge', 'x1e.32xlarge', 'x1e.4xlarge', 'x1e.8xlarge',
                'x1e.xlarge', 'z1d.12xlarge', 'z1d.2xlarge', 'z1d.3xlarge', 'z1d.6xlarge', 'z1d.large', 'z1d.metal', 'z1d.xlarge'
            ],
            default="t3.micro",
            description="The EC2 instance type for the Drupal server autoscaling group"
        )
        asg_desired_capacity_param = core.CfnParameter(
            self,
            "AppAsgDesiredCapacity",
            default=1,
            description="The initial capacity of the application Auto Scaling group at the time of its creation and the capacity it attempts to maintain.",
            min_value=0,
            type="Number"
        )
        asg_max_size_param = core.CfnParameter(
            self,
            "AppAsgMaxSize",
            default=2,
            description="The maximum size of the Auto Scaling group.",
            min_value=0,
            type="Number"
        )
        asg_min_size_param = core.CfnParameter(
            self,
            "AppAsgMinSize",
            default=1,
            description="The minimum size of the Auto Scaling group.",
            min_value=0,
            type="Number"
        )
        with open('drupal/scripts/app_launch_config_user_data.sh') as f:
            app_launch_config_user_data = f.read()
        launch_config = aws_autoscaling.CfnLaunchConfiguration(
            self,
            "AppLaunchConfig",
            image_id=AMI, # TODO: Put into CFN Mapping
            instance_type=app_instance_type_param.value_as_string,
            iam_instance_profile=instance_profile.ref,
            security_groups=[app_sg.ref],
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
            desired_capacity=asg_desired_capacity_param.value.to_string(),
            max_size=asg_max_size_param.value.to_string(),
            min_size=asg_min_size_param.value.to_string()
        )
        # https://github.com/aws/aws-cdk/issues/3615
        asg.add_override(
            "Properties.VPCZoneIdentifier",
            {
                "Fn::If": [
                    customer_vpc_given_condition.logical_id,
                    [
                        customer_vpc_private_subnet_id1.value.to_string(),
                        customer_vpc_private_subnet_id2.value.to_string()
                    ],
                    [
                        vpc_private_subnet1.ref,
                        vpc_private_subnet2.ref
                    ]
                ]
            }
        )
        asg.add_override(
            "Properties.TargetGroupARNs",
            {
                "Fn::If": [
                    certificate_arn_exists_condition.logical_id,
                    [https_target_group.ref],
                    [http_target_group.ref]
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
        asg.add_depends_on(db_cluster)
        asg_web_server_scale_up_policy = aws_autoscaling.CfnScalingPolicy(
            self,
            "WebServerScaleUpPolicy",
            adjustment_type="ChangeInCapacity",
            auto_scaling_group_name=asg.ref,
            cooldown="60",
            scaling_adjustment=1
        )
        asg_web_server_scale_down_policy = aws_autoscaling.CfnScalingPolicy(
            self,
            "WebServerScaleDownPolicy",
            adjustment_type="ChangeInCapacity",
            auto_scaling_group_name=asg.ref,
            cooldown="60",
            scaling_adjustment=-1
        )

        # cloudwatch alarms
        cpu_alarm_high = aws_cloudwatch.CfnAlarm(
            self,
            "CPUAlarmHigh",
            comparison_operator="GreaterThanThreshold",
            evaluation_periods=2,
            actions_enabled=None,
            alarm_actions=[ asg_web_server_scale_up_policy.ref, notification_topic.topic_arn ],
            alarm_description="Scale-up if CPU > 90% for 10mins",
            dimensions=[ aws_cloudwatch.CfnAlarm.DimensionProperty(
                name="AutoScalingGroupName",
                value=asg.ref
            )],
            metric_name="CPUUtilization",
            namespace="AWS/EC2",
            period=300,
            statistic="Average",
            threshold=90
        )
        cpu_alarm_low = aws_cloudwatch.CfnAlarm(
            self,
            "CPUAlarmLow",
            comparison_operator="LessThanThreshold",
            evaluation_periods=2,
            actions_enabled=None,
            alarm_actions=[ asg_web_server_scale_down_policy.ref, notification_topic.topic_arn ],
            alarm_description="Scale-down if CPU < 70% for 10mins",
            dimensions=[ aws_cloudwatch.CfnAlarm.DimensionProperty(
                name="AutoScalingGroupName",
                value=asg.ref
            )],
            metric_name="CPUUtilization",
            namespace="AWS/EC2",
            period=300,
            statistic="Average",
            threshold=70
        )

        sg_http_ingress = aws_ec2.CfnSecurityGroupIngress(
            self,
            "AppSgHttpIngress",
            from_port=80,
            group_id=app_sg.ref,
            ip_protocol="tcp",
            source_security_group_id=alb_sg.ref,
            to_port=80
        )
        sg_http_ingress.cfn_options.condition = certificate_arn_does_not_exist_condition

        sg_https_ingress = aws_ec2.CfnSecurityGroupIngress(
            self,
            "AppSgHttpsIngress",
            from_port=443,
            group_id=app_sg.ref,
            ip_protocol="tcp",
            source_security_group_id=alb_sg.ref,
            to_port=443
        )
        sg_https_ingress.cfn_options.condition = certificate_arn_exists_condition

        # cicd pipeline
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
                                    source_artifact_s3_bucket_param.value_as_string,
                                    source_artifact_s3_object_key_param.value_as_string
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
                                    source_artifact_s3_bucket_param.value_as_string
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
            service_role_arn=code_deploy_role.role_arn,
            trigger_configurations=[]
        )
        code_deploy_deployment_group.add_override("Properties.TriggerConfigurations",[
            {
                "TriggerEvents": [
                    "DeploymentSuccess",
                    "DeploymentRollback"
                ],
                "TriggerName": "DeploymentNotification",
                "TriggerTargetArn": notification_topic.topic_arn
            }
        ])

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
                                'S3Bucket': source_artifact_s3_bucket_param.value_as_string,
                                'S3ObjectKey': source_artifact_s3_object_key_param.value_as_string
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
            default="false",
        )
        elasticache_enable_condition = core.CfnCondition(
            self,
            "ElastiCacheEnableCondition",
            expression=core.Fn.condition_equals(elasticache_enable_param.value, "true")
        )
        elasticache_sg = aws_ec2.CfnSecurityGroup(
            self,
            "ElastiCacheSg",
            group_description="App SG"
        )
        elasticache_sg.add_override(
            "Properties.VpcId",
            {
                "Fn::If": [
                    customer_vpc_not_given_condition.logical_id,
                    vpc.ref,
                    customer_vpc_id_param.value.to_string()
                ]
            }
        )
        elasticache_sg.cfn_options.condition = elasticache_enable_condition
        elasticache_sg_ingress = aws_ec2.CfnSecurityGroupIngress(
            self,
            "ElasticacheSgIngress",
            from_port=11211,
            group_id=elasticache_sg.ref,
            ip_protocol="tcp",
            source_security_group_id=app_sg.ref,
            to_port=11211
        )
        elasticache_sg_ingress.cfn_options.condition = elasticache_enable_condition
        elasticache_subnet_group = core.CfnResource(
            self,
            "ElastiCacheSubnetGroup",
            type="AWS::ElastiCache::SubnetGroup",
            properties={
                "Description": "test",
                "SubnetIds":  {
                    "Fn::If": [
                        customer_vpc_not_given_condition.logical_id,
                        [
                            vpc_private_subnet1.ref,
                            vpc_private_subnet2.ref
                        ],
                        [
                            customer_vpc_private_subnet_id1.value.to_string(),
                            customer_vpc_private_subnet_id2.value.to_string()
                            
                        ]
                    ]
                }
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
            default="false",
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
                    domain_name=alb.attr_dns_name,
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
