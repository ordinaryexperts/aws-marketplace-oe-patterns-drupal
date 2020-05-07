import random
from aws_cdk import (
	aws_ec2,
	core
)

class VpcStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        self.vpc = aws_ec2.CfnVPC(
            self,
            "Vpc",
            cidr_block="10.0.0.0/16",
            enable_dns_hostnames=True,
            enable_dns_support=True,
            instance_tenancy="default",
            tags=[core.CfnTag(key="Name", value="{}/Vpc".format(self.stack_name))]
        )

        vpc_igw = aws_ec2.CfnInternetGateway(
            self,
            "VpcInternetGateway",
            tags=[core.CfnTag(key="Name", value="{}/Vpc".format(self.stack_name))]
        )
        vpc_igw.add_depends_on(self.vpc)
        vpc_igw_attachment = aws_ec2.CfnVPCGatewayAttachment(
            self,
            "VpcIGWAttachment",
            vpc_id=self.vpc.ref,
            internet_gateway_id=vpc_igw.ref
        )
        vpc_igw_attachment.add_depends_on(self.vpc)

        self.vpc_public_subnet1 = aws_ec2.CfnSubnet(
            self,
            "VpcPublicSubnet1",
            cidr_block="10.0.0.0/18",
            vpc_id=self.vpc.ref,
            assign_ipv6_address_on_creation=None,
            availability_zone="us-east-1a",
            map_public_ip_on_launch=True,
            tags=[
                core.CfnTag(key="Name", value="{}/Vpc/PublicSubnet1".format(self.stack_name)),
                core.CfnTag(key="aws-cdk:subnet-name", value="Public"),
                core.CfnTag(key="aws-cdk:subnet-type", value="Public")
            ]
        )
        self.vpc_public_subnet1.add_depends_on(self.vpc)
        vpc_public_subnet1_route_table = aws_ec2.CfnRouteTable(
            self,
            "VpcPublicSubnet1RouteTable",
            vpc_id=self.vpc.ref,
            tags=[core.CfnTag(key="Name", value="{}/Vpc/PublicSubnet1".format(self.stack_name))]
        )
        vpc_public_subnet1_route_table.add_depends_on(self.vpc)
        vpc_public_subnet1_route_table_association = aws_ec2.CfnSubnetRouteTableAssociation(
            self,
            "VpcPublicSubnet1RouteTableAssociation",
            route_table_id=vpc_public_subnet1_route_table.ref,
            subnet_id=self.vpc_public_subnet1.ref
        )
        vpc_public_subnet1_route_table_association.add_depends_on(vpc_public_subnet1_route_table)
        vpc_public_subnet1_default_route = aws_ec2.CfnRoute(
            self,
            "VpcPublicSubnet1DefaultRoute",
            route_table_id=vpc_public_subnet1_route_table.ref,
            destination_cidr_block="0.0.0.0/0",
            gateway_id=vpc_igw.ref
        )
        vpc_public_subnet1_default_route.add_depends_on(vpc_igw)

        self.vpc_public_subnet2 = aws_ec2.CfnSubnet(
            self,
            "VpcPublicSubnet2",
            cidr_block="10.0.64.0/18",
            vpc_id=self.vpc.ref,
            assign_ipv6_address_on_creation=None,
            availability_zone="us-east-1b",
            map_public_ip_on_launch=True,
            tags=[
                core.CfnTag(key="Name", value="{}/Vpc/PublicSubnet2".format(self.stack_name)),
                core.CfnTag(key="aws-cdk:subnet-name", value="Public"),
                core.CfnTag(key="aws-cdk:subnet-type", value="Public")
            ]
        )
        self.vpc_public_subnet2.add_depends_on(self.vpc)
        vpc_public_subnet2_route_table = aws_ec2.CfnRouteTable(
            self,
            "VpcPublicSubnet2RouteTable",
            vpc_id=self.vpc.ref,
            tags=[core.CfnTag(key="Name", value="{}/Vpc/PublicSubnet2".format(self.stack_name))]
        )
        vpc_public_subnet2_route_table.add_depends_on(self.vpc)
        vpc_public_subnet2_route_table_association = aws_ec2.CfnSubnetRouteTableAssociation(
            self,
            "VpcPublicSubnet2RouteTableAssociation",
            route_table_id=vpc_public_subnet2_route_table.ref,
            subnet_id=self.vpc_public_subnet2.ref
        )
        vpc_public_subnet2_route_table_association.add_depends_on(vpc_public_subnet2_route_table)
        vpc_public_subnet2_default_route = aws_ec2.CfnRoute(
            self,
            "VpcPublicSubnet2DefaultRoute",
            route_table_id=vpc_public_subnet2_route_table.ref,
            destination_cidr_block="0.0.0.0/0",
            gateway_id=vpc_igw.ref
        )
        vpc_public_subnet2_default_route.add_depends_on(vpc_igw)

        self.vpc_private_subnet1 = aws_ec2.CfnSubnet(
            self,
            "VpcPrivateSubnet1",
            cidr_block="10.0.128.0/18",
            vpc_id=self.vpc.ref,
            assign_ipv6_address_on_creation=None,
            availability_zone="us-east-1a",
            map_public_ip_on_launch=False,
            tags=[
                core.CfnTag(key="Name", value="{}/Vpc/PrivateSubnet1".format(self.stack_name)),
                core.CfnTag(key="aws-cdk:subnet-name", value="Private"),
                core.CfnTag(key="aws-cdk:subnet-type", value="Private")
            ]
        )
        self.vpc_private_subnet1.add_depends_on(self.vpc)
        vpc_private_subnet1_route_table = aws_ec2.CfnRouteTable(
            self,
            "VpcPrivateSubnet1RouteTable",
            vpc_id=self.vpc.ref,
            tags=[core.CfnTag(key="Name", value="{}/Vpc/PrivateSubnet1".format(self.stack_name))]
        )
        vpc_private_subnet1_route_table.add_depends_on(self.vpc)
        vpc_private_subnet1_route_table_association = aws_ec2.CfnSubnetRouteTableAssociation(
            self,
            "VpcPrivateSubnet1RouteTableAssociation",
            route_table_id=vpc_private_subnet1_route_table.ref,
            subnet_id=self.vpc_private_subnet1.ref
        )
        vpc_private_subnet1_route_table_association.add_depends_on(vpc_private_subnet1_route_table)

        self.vpc_private_subnet2 = aws_ec2.CfnSubnet(
            self,
            "VpcPrivateSubnet2",
            cidr_block="10.0.192.0/18",
            vpc_id=self.vpc.ref,
            assign_ipv6_address_on_creation=None,
            availability_zone="us-east-1b",
            map_public_ip_on_launch=False,
            tags=[
                core.CfnTag(key="Name", value="{}/Vpc/PrivateSubnet2".format(self.stack_name)),
                core.CfnTag(key="aws-cdk:subnet-name", value="Private"),
                core.CfnTag(key="aws-cdk:subnet-type", value="Private")
            ]
        )
        self.vpc_private_subnet2.add_depends_on(self.vpc)
        vpc_private_subnet2_route_table = aws_ec2.CfnRouteTable(
            self,
            "VpcPrivateSubnet2RouteTable",
            vpc_id=self.vpc.ref,
            tags=[core.CfnTag(key="Name", value="{}/Vpc/PrivateSubnet2".format(self.stack_name))]
        )
        vpc_private_subnet2_route_table.add_depends_on(self.vpc)
        vpc_private_subnet2_route_table_association = aws_ec2.CfnSubnetRouteTableAssociation(
            self,
            "VpcPrivateSubnet2RouteTableAssociation",
            route_table_id=vpc_private_subnet2_route_table.ref,
            subnet_id=self.vpc_private_subnet2.ref
        )
        vpc_private_subnet2_route_table_association.add_depends_on(vpc_private_subnet2_route_table)



