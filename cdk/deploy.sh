#!/usr/bin/env bash

source .env/bin/activate
aws-vault exec oe-patterns-dev -- cdk deploy --parameters CertificateArn=arn:aws:acm:us-west-1:992593896645:certificate/9a8d0ee2-9619-45b6-af09-0a78bb813d1a
