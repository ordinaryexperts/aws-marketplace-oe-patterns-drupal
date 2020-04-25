#!/usr/bin/env bash

source .env/bin/activate
aws-vault exec oe-patterns-dev -- cdk synth
