import random
from aws_cdk import (
	aws_ec2,
	core
)

class VpcStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

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
        cloudfront_certificate_arn_param = core.CfnParameter(
            self,
            "CloudFrontCertificateArn",
            default="",
            description="The ARN from AWS Certificate Manager for the SSL cert used in CloudFront CDN. Must be in us-east region."
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
            tags=[core.CfnTag(key="Name", value="{}/Vpc".format(self.stack_name))]
        )
        vpc.cfn_options.condition=customer_vpc_not_given_condition

        vpc_igw = aws_ec2.CfnInternetGateway(
            self,
            "VpcInternetGateway",
            tags=[core.CfnTag(key="Name", value="{}/Vpc".format(self.stack_name))]
        )
        vpc_igw.cfn_options.condition=customer_vpc_not_given_condition
        vpc_igw_attachment = aws_ec2.CfnVPCGatewayAttachment(
            self,
            "VpcIGWAttachment",
            vpc_id=vpc.ref,
            internet_gateway_id=vpc_igw.ref
        )
        vpc_igw_attachment.cfn_options.condition=customer_vpc_not_given_condition

        vpc_public_subnet1 = aws_ec2.CfnSubnet(
            self,
            "VpcPublicSubnet1",
            cidr_block="10.0.0.0/18",
            vpc_id=vpc.ref,
            assign_ipv6_address_on_creation=None,
            availability_zone="us-east-1a",
            map_public_ip_on_launch=True,
            tags=[
                core.CfnTag(key="Name", value="{}/Vpc/PublicSubnet1".format(self.stack_name)),
                core.CfnTag(key="aws-cdk:subnet-name", value="Public"),
                core.CfnTag(key="aws-cdk:subnet-type", value="Public")
            ]
        )
        vpc_public_subnet1.cfn_options.condition=customer_vpc_not_given_condition
        vpc_public_subnet1_route_table = aws_ec2.CfnRouteTable(
            self,
            "VpcPublicSubnet1RouteTable",
            vpc_id=vpc.ref,
            tags=[core.CfnTag(key="Name", value="{}/Vpc/PublicSubnet1".format(self.stack_name))]
        )
        vpc_public_subnet1_route_table.cfn_options.condition=customer_vpc_not_given_condition
        vpc_public_subnet1_route_table_association = aws_ec2.CfnSubnetRouteTableAssociation(
            self,
            "VpcPublicSubnet1RouteTableAssociation",
            route_table_id=vpc_public_subnet1_route_table.ref,
            subnet_id=vpc_public_subnet1.ref
        )
        vpc_public_subnet1_route_table_association.cfn_options.condition=customer_vpc_not_given_condition
        vpc_public_subnet1_default_route = aws_ec2.CfnRoute(
            self,
            "VpcPublicSubnet1DefaultRoute",
            route_table_id=vpc_public_subnet1_route_table.ref,
            destination_cidr_block="0.0.0.0/0",
            gateway_id=vpc_igw.ref
        )
        vpc_public_subnet1_default_route.cfn_options.condition=customer_vpc_not_given_condition
        vpc_public_subnet1_eip = aws_ec2.CfnEIP(
            self,
            "VpcPublicSubnet1EIP",
            domain="vpc",
            tags=[core.CfnTag(key="Name", value="{}/Vpc/PublicSubnet1".format(self.stack_name))]
        )
        vpc_public_subnet1_nat_gateway = aws_ec2.CfnNatGateway(
            self,
            "VpcPublicSubnet1NATGateway",
            allocation_id=vpc_public_subnet1_eip.attr_allocation_id,
            subnet_id=vpc_public_subnet1.ref,
            tags=[core.CfnTag(key="Name", value="{}/Vpc/PublicSubnet1".format(self.stack_name))]
        )
        vpc_public_subnet1_nat_gateway.cfn_options.condition=customer_vpc_not_given_condition

        vpc_public_subnet2 = aws_ec2.CfnSubnet(
            self,
            "VpcPublicSubnet2",
            cidr_block="10.0.64.0/18",
            vpc_id=vpc.ref,
            assign_ipv6_address_on_creation=None,
            availability_zone="us-east-1b",
            map_public_ip_on_launch=True,
            tags=[
                core.CfnTag(key="Name", value="{}/Vpc/PublicSubnet2".format(self.stack_name)),
                core.CfnTag(key="aws-cdk:subnet-name", value="Public"),
                core.CfnTag(key="aws-cdk:subnet-type", value="Public")
            ]
        )
        vpc_public_subnet2.cfn_options.condition=customer_vpc_not_given_condition
        vpc_public_subnet2_route_table = aws_ec2.CfnRouteTable(
            self,
            "VpcPublicSubnet2RouteTable",
            vpc_id=vpc.ref,
            tags=[core.CfnTag(key="Name", value="{}/Vpc/PublicSubnet2".format(self.stack_name))]
        )
        vpc_public_subnet2_route_table.cfn_options.condition=customer_vpc_not_given_condition
        vpc_public_subnet2_route_table_association = aws_ec2.CfnSubnetRouteTableAssociation(
            self,
            "VpcPublicSubnet2RouteTableAssociation",
            route_table_id=vpc_public_subnet2_route_table.ref,
            subnet_id=vpc_public_subnet2.ref
        )
        vpc_public_subnet2_route_table_association.cfn_options.condition=customer_vpc_not_given_condition
        vpc_public_subnet2_default_route = aws_ec2.CfnRoute(
            self,
            "VpcPublicSubnet2DefaultRoute",
            route_table_id=vpc_public_subnet2_route_table.ref,
            destination_cidr_block="0.0.0.0/0",
            gateway_id=vpc_igw.ref
        )
        vpc_public_subnet2_default_route.cfn_options.condition=customer_vpc_not_given_condition
        vpc_public_subnet2_eip = aws_ec2.CfnEIP(
            self,
            "VpcPublicSubnet2EIP",
            domain="vpc",
            tags=[core.CfnTag(key="Name", value="{}/Vpc/PublicSubnet2".format(self.stack_name))]
        )
        vpc_public_subnet2_nat_gateway = aws_ec2.CfnNatGateway(
            self,
            "VpcPublicSubnet2NATGateway",
            allocation_id=vpc_public_subnet2_eip.attr_allocation_id,
            subnet_id=vpc_public_subnet1.ref,
            tags=[core.CfnTag(key="Name", value="{}/Vpc/PublicSubnet2".format(self.stack_name))]
        )
        vpc_public_subnet2_nat_gateway.cfn_options.condition=customer_vpc_not_given_condition

        vpc_private_subnet1 = aws_ec2.CfnSubnet(
            self,
            "VpcPrivateSubnet1",
            cidr_block="10.0.128.0/18",
            vpc_id=vpc.ref,
            assign_ipv6_address_on_creation=None,
            availability_zone="us-east-1a",
            map_public_ip_on_launch=False,
            tags=[
                core.CfnTag(key="Name", value="{}/Vpc/PrivateSubnet1".format(self.stack_name)),
                core.CfnTag(key="aws-cdk:subnet-name", value="Private"),
                core.CfnTag(key="aws-cdk:subnet-type", value="Private")
            ]
        )
        vpc_private_subnet1.cfn_options.condition=customer_vpc_not_given_condition
        vpc_private_subnet1_route_table = aws_ec2.CfnRouteTable(
            self,
            "VpcPrivateSubnet1RouteTable",
            vpc_id=vpc.ref,
            tags=[core.CfnTag(key="Name", value="{}/Vpc/PrivateSubnet1".format(self.stack_name))]
        )
        vpc_private_subnet1_route_table.cfn_options.condition=customer_vpc_not_given_condition
        vpc_private_subnet1_route_table_association = aws_ec2.CfnSubnetRouteTableAssociation(
            self,
            "VpcPrivateSubnet1RouteTableAssociation",
            route_table_id=vpc_private_subnet1_route_table.ref,
            subnet_id=vpc_private_subnet1.ref
        )
        vpc_private_subnet1_route_table_association.cfn_options.condition=customer_vpc_not_given_condition

        vpc_private_subnet2 = aws_ec2.CfnSubnet(
            self,
            "VpcPrivateSubnet2",
            cidr_block="10.0.192.0/18",
            vpc_id=vpc.ref,
            assign_ipv6_address_on_creation=None,
            availability_zone="us-east-1b",
            map_public_ip_on_launch=False,
            tags=[
                core.CfnTag(key="Name", value="{}/Vpc/PrivateSubnet2".format(self.stack_name)),
                core.CfnTag(key="aws-cdk:subnet-name", value="Private"),
                core.CfnTag(key="aws-cdk:subnet-type", value="Private")
            ]
        )
        vpc_private_subnet2.cfn_options.condition=customer_vpc_not_given_condition
        vpc_private_subnet2_route_table = aws_ec2.CfnRouteTable(
            self,
            "VpcPrivateSubnet2RouteTable",
            vpc_id=vpc.ref,
            tags=[core.CfnTag(key="Name", value="{}/Vpc/PrivateSubnet2".format(self.stack_name))]
        )
        vpc_private_subnet2_route_table.cfn_options.condition=customer_vpc_not_given_condition
        vpc_private_subnet2_route_table_association = aws_ec2.CfnSubnetRouteTableAssociation(
            self,
            "VpcPrivateSubnet2RouteTableAssociation",
            route_table_id=vpc_private_subnet2_route_table.ref,
            subnet_id=vpc_private_subnet2.ref
        )
        vpc_private_subnet2_route_table_association.cfn_options.condition=customer_vpc_not_given_condition

        vpc_output = core.CfnOutput(
            self,
            "VpcOutput",
            condition=customer_vpc_not_given_condition,
            description="The default VPC created by stack.",
            export_name="{}-vpc".format(self.stack_name),
            value=vpc.ref
        )
        vpc_output = core.CfnOutput(
            self,
            "VpcOutputCustomer",
            condition=customer_vpc_given_condition,
            description="Empty VPC if customer VPC given.",
            export_name="{}-vpc".format(self.stack_name),
            value=''
        )
        private_subnet1_output = core.CfnOutput(
            self,
            "PrivateSubnet1Output",
            condition=customer_vpc_not_given_condition,
            description="The default private subnet1 created by stack.",
            export_name="{}-private-subnet1".format(self.stack_name),
            value=vpc_private_subnet1.ref
        )
        private_subnet1_output = core.CfnOutput(
            self,
            "PrivateSubnet1OutputCustomer",
            condition=customer_vpc_given_condition,
            description="Empty private subnet1 if customer VPC given.",
            export_name="{}-private-subnet1".format(self.stack_name),
            value=''
        )
        private_subnet2_output = core.CfnOutput(
            self,
            "PrivateSubnet2Output",
            condition=customer_vpc_not_given_condition,
            description="The default private subnet2 created by stack.",
            export_name="{}-private-subnet2".format(self.stack_name),
            value=vpc_private_subnet2.ref
        )
        private_subnet2_output = core.CfnOutput(
            self,
            "PrivateSubnet2OutputCustomer",
            condition=customer_vpc_given_condition,
            description="Empty private subnet2 if customer VPC given.",
            export_name="{}-private-subnet2".format(self.stack_name),
            value=''
        )
        public_subnet1_output = core.CfnOutput(
            self,
            "PublicSubnet1Output",
            condition=customer_vpc_not_given_condition,
            description="The default public subnet1 created by stack.",
            export_name="{}-public-subnet1".format(self.stack_name),
            value=vpc_public_subnet1.ref
        )
        public_subnet1_output = core.CfnOutput(
            self,
            "PublicSubnet1OutputCustomer",
            condition=customer_vpc_given_condition,
            description="Empty public subnet1 if customer VPC given.",
            export_name="{}-public-subnet1".format(self.stack_name),
            value=''
        )
        public_subnet2_output = core.CfnOutput(
            self,
            "PublicSubnet2Output",
            condition=customer_vpc_not_given_condition,
            description="The default public subnet2 created by stack.",
            export_name="{}-public-subnet2".format(self.stack_name),
            value=vpc_public_subnet2.ref
        )
        public_subnet1_output = core.CfnOutput(
            self,
            "PublicSubnet2OutputCustomer",
            condition=customer_vpc_given_condition,
            description="Empty public subnet2 if customer VPC given.",
            export_name="{}-public-subnet2".format(self.stack_name),
            value=''
        )
