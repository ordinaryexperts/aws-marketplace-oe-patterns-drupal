#!/usr/bin/env python3

import os
from aws_cdk import core

from drupal.drupal_stack import DrupalStack

# OE AWS Marketplace Patterns Dev
# arn:aws:organizations::440643590597:account/o-kqeqlsvu0w/992593896645
# ~/.aws/config
# [profile oe-patterns-dev]
# region=us-west-1
# role_arn=arn:aws:iam::992593896645:role/OrganizationAccountAccessRole
# source_profile=oe-prod
env_oe_patterns_dev_us_west_1 = core.Environment(account="992593896645", region="us-west-1")

app = core.App()
DrupalStack(app, "oe-patterns-drupal-{}".format(os.environ['USER']), env=env_oe_patterns_dev_us_west_1)

app.synth()
