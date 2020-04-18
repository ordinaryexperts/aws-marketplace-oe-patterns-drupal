from aws_cdk import core
from aws_cdk import aws_ec2 as ec2

class DrupalStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        vpc = ec2.Vpc(
            self,
            "vpc",
            cidr="10.0.0.0/16"
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
