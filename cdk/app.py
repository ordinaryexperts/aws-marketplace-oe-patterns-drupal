#!/usr/bin/env python3

import os
from aws_cdk import core

from drupal.drupal_stack import DrupalStack
from drupal.vpc_stack import VpcStack

# OE AWS Marketplace Patterns Dev
# arn:aws:organizations::440643590597:account/o-kqeqlsvu0w/992593896645
# ~/.aws/config
# [profile oe-patterns-dev]
# region=us-east-1
# role_arn=arn:aws:iam::992593896645:role/OrganizationAccountAccessRole
# source_profile=oe-prod
env_oe_patterns_dev_us_east_1 = core.Environment(account="992593896645", region="us-east-1")

app = core.App()

vpc_stack = VpcStack(app, "oe-patterns-vpc-{}".format(os.environ['USER']), env=env_oe_patterns_dev_us_east_1)
DrupalStack(app, "oe-patterns-drupal-{}".format(os.environ['USER']),
			env=env_oe_patterns_dev_us_east_1,
			vpc=vpc_stack.vpc,
			public_subnet1=vpc_stack.vpc_public_subnet1,
			public_subnet2=vpc_stack.vpc_public_subnet2,
			private_subnet1=vpc_stack.vpc_private_subnet1,
			private_subnet2=vpc_stack.vpc_private_subnet2)

app.synth()
