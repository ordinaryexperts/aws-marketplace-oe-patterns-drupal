# Ordinary Experts Drupal 8 on AWS Pattern

## Setup

    $ npm install -g aws-cdk
    $ cd cdk
    $ python3 -m venv .env
    $ source .env/bin/activate
    $ pip install -r requirements.txt

## Deploying

    $ cd cdk
    $ source .env/bin/activate
    $ aws-vault exec oe-prod-us-west-1 cdk deploy
