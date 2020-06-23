#!/usr/bin/env bash

# https://stackoverflow.com/a/246128
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

if [ "$#" -ne 1 ]; then
    VERSION=`git describe`
else
    VERSION=$1
fi

mkdir -p $DIR/../dist
cd $DIR/../cdk
cdk synth \
    --version-reporting false\
    --path-metadata false \
    --asset-metadata false > $DIR/../dist/template.yaml
cd $DIR/..
aws s3 cp dist/template.yaml \
	s3://deployment-user-and-buck-deploymentartifactbucket-17r9c9e9pu794/$VERSION/oe-drupal-patterns-template.yaml \
	--sse aws:kms --acl public-read
echo "Copied to https://deployment-user-and-buck-deploymentartifactbucket-17r9c9e9pu794.s3.amazonaws.com/$VERSION/oe-drupal-patterns-template.yaml"
