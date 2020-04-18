#!/usr/bin/env python3

from aws_cdk import core

from drupal.drupal_stack import DrupalStack


app = core.App()
DrupalStack(app, "drupal")

app.synth()
