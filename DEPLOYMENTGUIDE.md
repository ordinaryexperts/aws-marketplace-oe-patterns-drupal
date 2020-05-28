# Ordinary Experts Drupal 8 on AWS Deployment Guide

This AWS Marketplace template was created by Amazon Web Services Partners at Ordinary Experts with the aim of providing cloud developers a comprehensive AWS infrastructure that follows AWS best practices.

- [Overview](#overview)
  * [Amazon Web Services and Drupal](#amazon-web-services-and-drupal)
  * [Cost and Licenses](#cost-and-licenses)
- [Architecture](#architecture)
  * [AWS Resources](#aws-resources)
  * [Infrastructure](#infrastructure)
- [Planning the Deployment](#planning-the-deployment)
- [Deployment Options](#deployment-options)
  * [Enable Routing via HTTPS](#to-enable-routing-via-https)
  * [Use an Existing VPC](#to-use-an-existing-vpc)
  * [Use Existing Snapshot and Secrets](#to-configure-database-with-existing-snapshot-and-secrets)
  * [Use and Configure ElastiCache](#to-use-elasticache-and-configure-resource)
  * [Use and Configure CloudFront](#to-use-cloudfront-and-configure-resource)
  * [Configure Auto Scaling Groups](#to-configure-auto-scaling-groups)
- [Security](#security)
- [Troubleshooting](#troubleshooting)
- [Additional Resources](#additional-resources)
- [Document Revisions](#document-revisions)

## Overview

### Amazon Web Services and Drupal

The Ordinary Experts Drupal 8 Pattern is an open-source AWS CloudFormation template that offers an easy-to-install AWS infrastructure solution for quickly deploying a Drupal 8 project, using both AWS and Drupal best practices. The template makes it easy to spin up a production-ready, full-feature infrastructure ready to host scalable Drupal 8 application in the AWS cloud.

Drupal is a free and open-source web content management framework written in PHP, providing powerful tools to meet a broad range of web application needs. This template provides a base Drupal 8 application which can be customized or can be provided with an existing Drupal project. For more information about Drupal and installation guides, please refer to the official [Drupal documentation](https://www.drupal.org/documentation).

You can use this template to:
* Deploy a full-scale AWS infrastructure to create all necessary components for running a Drupal project
* Deploy Drupal using your existing VPC
* Optionally configure AWS resources to better suit your requirements

This guide discusses best practices for deploying Drupal on AWS using the specific resources in our infrastructure architecture. These resources include Amazon Elastic Compute Cloud (Amazon EC2), Amazon Virtual Public Cloud (Amazon VPC), Amazon Aurora Serverless, Amazon Elastic File System (Amazon EFS), Amazon Simple Storage System (Amazon S3), AWS CodePipeline, AWS CodeDeploy, Amazon Secrets Manager, Amazon ElastiCache, and Amazon CloudFront.

### Cost and Licenses

This deployment launches Drupal 8 automatically into a configuration of your choice. Drupal is open-source software licensed under GNU GPL version 2. For information about Drupal’s licensing, please refer to [Drupal’s license documentation](https://www.drupal.org/about/licensing#q1). You are responsible for the cost of AWS services used while running this template and a subscription fee for using our template. For a detailed cost breakdown and estimate, please refer to the infrastructure pricing estimation calculator on our Marketplace product page. Prices are subject to change.

## Architecture

### AWS Resources

The core AWS components in our architecture include the following AWS services:
* **AWS Identity Access Management (AWS IAM)** — Used for managing resource access and actions
* **Amazon Elastic Compute Cloud (Amazon EC2)** — Launch virtual machine instances with necessary programs installed and configured for Drupal to run
* **AWS Auto Scaling Groups** — Automatically provision EC2 instances based on CPU load in order to maintain high availability and optimal resource utilization
* **Elastic Load Balancing** — Automatically distribute traffic across available healthy EC2 instances to provide low latency and optimal performance
* **Amazon Virtual Public Cloud (Amazon VPC)** — Provision a private section of the AWS Cloud to launch AWS resources in a customized environment. By default, our stack creates two private and two public subnets, NAT Gateways, Internet Gateways, and associated route tables but it can also accept existing VPC and subnet IDs.
* **Amazon Aurora Serverless** — Automatically scales compute and capacity resources needed for the MySQL database. By default, our stack creates a new database but it can also accept an existing snapshot ARN.
* **Amazon Elastic File System (Amazon EFS)** — Used to share user generated content between application servers.
* **Amazon Simple Storage System (Amazon S3)** — Used to hold pipeline artifacts and store the source artifact for AWS CodePipeline. The source zip is your compressed Drupal project which is either uploaded manually or via another pipeline to the S3 bucket. When the source zip file is changed, the pipeline will be triggered to run.
* **AWS CodePipeline** — Stack CI/CD polls the source zip in S3 for changes and uses CodeDeploy to deploy the updated source zip into Auto Scaling Group.
* **AWS CodeDeploy** — Deploy action launches the updated source zip into the associated Auto Scaling Group and sends email to subscription email notifying deployment success or rollback.
* **Amazon Secrets Manager** — Auto-generate database username and password without storing hard-coded values to guarantee high level of security.
* **Amazon ElastiCache** — Optional memcached in-memory data storage
* **Amazon CloudFront** — Optional static content delivery network to provide viewers with low latency and high speed access to data, videos, applications, and APIs on your Drupal application.
* **Amazon Simple Notification Service (Amazon SNS)** — Optional email notification service to receive various notifications for AWS resource alerts if subscription email has been provided.
* **Amazon CloudWatch** — Logging and monitoring for AWS resource utilization and application logs.  Connected to Amazon SNS to provide alerts via an optional subscription email.

### Infrastructure

Deploying this template for a new virtual private cloud (VPC) with all optional resources provisioned builds the following Drupal 8 environment in the AWS Cloud.

![Ordinary Experts Drupal Pattern Topology Diagram](oe_drupal_patterns_topology_diagram.png)*Figure 1: Ordinary Experts Drupal Pattern Architecture*

Automatically configured to support auto-scaling through AWS Autoscaling Groups, our solution leverages an EFS file system to share user generated content between application servers. We support multiple availability zones using an RDS Aurora serverless cluster and Amazon's integrated options to distribute infrastructure. Additionally, our solution includes a CodePipeline which actively monitors a deployment location on AWS S3 making continuous integration and deployment throughout your infrastructure easy.

Optional configurations include the following:

* Integration of CloudFront as a CDN solution
* ElastiCache caching layer, ready for easy configuration with the CDN and memcached modules for Drupal.
* Contain your Drupal infrastructure in a new VPC, or provide this CloudFront stack with an existing VPC id and subnets.
* Support for SSL by supplying the ARN of an existing certificate from AWS Certificate Manager.

## Planning the Deployment

Prior to deploying your Drupal application, the stack needs the following resources to be set-up and provided during deployment.

* **SourceArtifactS3Bucket** (*string*):
  - The name of the S3 bucket to hold the project source zip.
  - By default it will point to the Ordinary Experts Drupal bucket which you can use to test how the Drupal application will be launched.
  - In order for your project pipeline to work with your project source, the artifact bucket will need to be set up outside of the stack and provided as a parameter.
* **SourceArtifactS3ObjectKey** (*string*):
  - The S3 object key of the project source zip.
  - By default it will point to the Ordinary Experts Drupal project source zip which you can use to test how the Drupal application will be launched.
  - In order for your project pipeline to work with your project source, the project will need to be uploaded to the corresponding bucket via a separate pipeline or manually each time a new version needs to be launched.

## Deployment Options

As stated previously, our template will provision a VPC with all associated components, AWS ASGs to launch EC2 instances, an ELB to manage web traffic, a fully auto-scaling Aurora Serverless MySQL database, AWS EFS for server-shared file storage, a complete CI/CD pipeline using S3 and CodeDeploy, and comprehensive application logging and resource monitoring via CloudWatch.

The following optional parameters are accepted by the template to further customize the application stack.

##### To enable routing via HTTPS:


##### To use an existing VPC:

##### To configure database with existing snapshot and secrets:

##### To use ElastiCache and configure resource:

##### To use CloudFront and configure resource:

##### To configure Auto Scaling Groups:

## Security

This is an h1 heading

## Troubleshooting

This is an h1 heading

## Additional Resources

This is an h1 heading

## Document Revisions

This is an h1 heading
