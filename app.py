#!/usr/bin/env python3

from aws_cdk import core

from drupal.drupal_stack import DrupalStack

env_us_west_1 = core.Environment(account="440643590597", region="us-west-1")

app = core.App()
DrupalStack(app, "drupal", env=env_us_west_1)

app.synth()
