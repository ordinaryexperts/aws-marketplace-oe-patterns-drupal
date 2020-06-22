
# Development Guide

This guide is for developers of the OE Drupal Pattern.

## Setup

We are following the [3 Musketeers](https://3musketeers.io/) pattern for project layout / setup.

First, install [Docker](https://www.docker.com/), [Docker Compose](https://docs.docker.com/compose/), and [Make](https://www.gnu.org/software/make/).

Then:

    $ make build
    $ make synth
    $ aws-vault exec oe-patterns-dev -- make deploy

## How to release a new version

1. Create release branch with `git flow release start [version]`
1. Update CHANGELOG.md on release branch
1. Commit changes to CHANGELOG.md (will update `git describe`)
1. Build AMI in production account with `ave oe-patterns-prod make ami-ec2-build`
1. Update `drupal_stack.py` with updated AMI ID as instructed
1. Generate PLF row using AMI ID and release version with `ave oe-patterns-dev make AMI_ID=$AMI_ID TEMPLATE_VERSION=$TEMPLATE_VERSION gen-plf`
1. Commit changes to release branch
1. Finish release branch with `git flow release finish [version]`
1. Publish CFN template to production account using `ave oe-patterns-prod make publish`