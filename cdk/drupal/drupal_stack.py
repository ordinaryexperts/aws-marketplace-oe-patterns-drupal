import json
from aws_cdk import aws_autoscaling as autoscaling
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_elasticloadbalancing as elasticloadbalancing
from aws_cdk import aws_iam as iam
from aws_cdk import aws_rds as rds
from aws_cdk import aws_secretsmanager as secretsmanager
from aws_cdk import aws_sns as sns
from aws_cdk import core

class DrupalStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        vpc = ec2.Vpc(
            self,
            "vpc",
            cidr="10.0.0.0/16"
        )
        secret = secretsmanager.Secret(
            self,
            "secret",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template=json.dumps({"username":"user"}),
                generate_string_key="password"
            )
        )
        db_subnet_group = rds.CfnDBSubnetGroup(
            self,
            "DBSubnetGroup",
            db_subnet_group_description="test",
            subnet_ids=vpc.select_subnets(subnet_type=ec2.SubnetType.PRIVATE).subnet_ids
        )
        db_cluster_parameter_group = rds.CfnDBClusterParameterGroup(
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
        db_cluster = rds.CfnDBCluster(
            self,
            "DBCluster",
            engine="aurora",
            db_cluster_parameter_group_name=db_cluster_parameter_group.ref,
            db_subnet_group_name=db_subnet_group.ref,
            engine_mode="serverless",
            master_username="dbadmin",
            # TODO: get this working
            # master_user_password=core.SecretValue.cfnDynamicReference(secret),
            master_user_password="dbpassword",
            scaling_configuration={
                "auto_pause": True,
                "min_capacity": 1,
                "max_capacity": 2,
                "seconds_until_auto_pause": 30
            },
            storage_encrypted=True
        )
        notification_topic = sns.Topic(
            self,
            "NotificationTopic"
        )
        app_instance_role = iam.Role(
            self,
            "AppInstanceRole",
            assumed_by=iam.ServicePrincipal('ec2.amazonaws.com'),
            inline_policies={
                "AllowStreamMetricsToCloudWatch": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                'cloudwatch:GetMetricStatistics',
                                'cloudwatch:ListMetrics',
                                'cloudwatch:PutMetricData'
                            ],
                            resources=['*']
                        )
                    ]
                )
            }
        )
        amis = ec2.MachineImage.generic_linux({
            "us-west-1": "ami-08e38d38bafbb63f1"
        })
        asg = autoscaling.AutoScalingGroup(
            self,
            "AppAsg",
            instance_type=ec2.InstanceType("t3.micro"),
            machine_image=amis,
            role=app_instance_role,
            vpc=vpc
        )
        lb = elasticloadbalancing.LoadBalancer(
            self,
            "AppAlb",
            vpc=vpc
        )
        lb.add_target(asg)
        listener = lb.add_listener(
            external_port=80
        )
        listener.connections.allow_default_port_from_any_ipv4("Open to the world")
