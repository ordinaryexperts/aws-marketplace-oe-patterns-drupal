from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_rds as rds
from aws_cdk import aws_secretsmanager as secretsmanager
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
            "secret"
        )
        db_subnet_group = rds.CfnDBSubnetGroup(
            self,
            "DBSubnetGroup",
            db_subnet_group_description="test",
            subnet_ids=vpc.select_subnets(subnet_type=ec2.SubnetType.PRIVATE).subnet_ids
        )
        # rds = ec2.Rds(
        #     self,
        #     "rds"
        # )
        # alb = alb(
        #     self,
        #     "alb"
        # )
        # asg = asg(
        #     self,
        #     "asg"
        # )
