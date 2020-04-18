# Ordinary Experts Drupal 8 on AWS Pattern

## Setup

    $ cd cdk
    $ python3 -m venv .env
    $ pip install -r requirements.txt

## Deploying

    $ cd cdk
    $ source .env/bin/activate
    $ pip
    $ aws-vault exec oe-prod-us-west-1 cdk deploy
