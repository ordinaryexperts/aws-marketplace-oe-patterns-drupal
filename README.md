# Ordinary Experts Drupal 8 on AWS Pattern

## Drupal Stack

The Ordinary Experts Drupal 8 Pattern is an open-source AWS CloudFormation template that offers an easy-to-install AWS infrastructure solution for quickly deploying a Drupal 8 project, using both AWS and Drupal best practices. The template makes it easy to spin up a production-ready, full-feature infrastructure ready to host scalable Drupal 8 app in the AWS cloud.

Drupal is a free and open-source web content management framework written in PHP, providing powerful tools to meet a broad range of web application needs. This template provides a base Drupal 8 application or can be provided with an existing Drupal project.

The AWS stack uses Amazon Elastic Compute Cloud (Amazon EC2), Amazon Virtual Public Cloud (Amazon VPC), Amazon Aurora Serverless, Amazon Elastic File System (Amazon EFS), Amazon Simple Storage System (Amazon S3), AWS CodePipeline, AWS CodeDeploy, Amazon Secrets Manager, Amazon ElastiCache, and Amazon CloudFront.

Automatically configured to support auto-scaling through AWS Autoscaling Groups, this solution leverages an EFS file system to share user generated content between application servers. Additionally, our solution includes a CodePipeline which actively monitors a deployment location on AWS S3 making continuous integration and deployment throughout your infrastructure easy.

We support multiple availability zones using an RDS Aurora serverless cluster and Amazon's integrated options to distribute infrastructure.

Regions supported by Ordinary Experts' stack:

| Fully Supported | Unsupported |
| -------------- | ----------- |
| <ul><li>us-east-1 (N. Virginia)</li><li>us-east-2 (Ohio)</li><li>us-west-1 (N. California)</li><li>us-west-2 (Oregon)</li><li>ca-central-1 (Central)</li><li>eu-central-1 (Frankfurt)</li><li>eu-west-1 (Ireland)</li><li>eu-west-2 (London)</li><li>eu-west-3 (Paris)</li><li>ap-northeast-1 (Tokyo)</li><li>ap-south-1 (Mumbai)</li><li>ap-southeast-1 (Singapore)</li><li>ap-southeast-2 (Sydney)</li></ul> | <ul><li>eu-north-1 (Stockholm)</li><li>eu-south-1 (Milan)</li><li>ap-east-1 (Hong Kong)</li><li>me-south-1 (Bahrain)</li><li>af-south-1 (Cape Town)</li><li>sa-east-1 (Sao Paolo)</li><li>ap-northeast-2 (Seoul):</br>requires subnets in<br>specific AZs to run<br> Aurora Serverless.</li></ul> |


Optional configurations include the following:
* Integration of CloudFront as a CDN solution
* ElastiCache caching layer, ready for easy configuration with the CDN and memcached modules for Drupal.
* Contain your Drupal infrastructure in a new VPC, or provide this CloudFront stack with an existing VPC id and subnets.
* Support for SSL by supplying the ARN of an existing certificate from AWS Certificate Manager.

Comprehensive, professional cloud hosting for Drupal at the click of a button.

![Ordinary Experts Drupal Pattern Topology Diagram](oe_drupal_patterns_topology_diagram.png)

## Setup

We are following the [3 Musketeers](https://3musketeers.io/) pattern for project layout / setup.

First, install [Docker](https://www.docker.com/), [Docker Compose](https://docs.docker.com/compose/), and [Make](https://www.gnu.org/software/make/).

Then:

    $ make build
    $ make synth
    $ aws-vault exec oe-patterns-dev -- make deploy

## Deployment Guide
Detailed information about the architecture and step-by-step instructions are available on [our deployment guide](DEPLOYMENTGUIDE.md).

## Feedback
To post feedback, submit feature ideas, or report bugs, use the Issues section of this GitHub repo.
