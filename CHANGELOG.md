# Unreleased

* Schedule nightly workflow to test all scenarios; test all resources in main workflow
* Expand test support into other regions

# 0.2.0

* DB snapshot and secret ARN rule validation
* Update Github CI to always upload test artifact
* Expand test scenarios
* Add topology diagram to README.md
* Add make publish command to push to s3 distribution bucket
* Add PipelineArtifactBucketName param
* Add AMI copy-image and CFN mappings
* Add CodeBuild appspec.yml generation
* AMI hardening / security checklist
* Encryption

# 0.1.0

* Initial commit
* Add SSL support
* Add CloudWatch Logs support
* Initial CICD Pipeline
* Do not use custom names for security groups
* Upgrade CDK to 1.36.1
* Add CloudFront support
* Move to us-east-1
* Notifications for deployments
* Elasticache and Cloudfront disabled by default
* Autoscaling alarms triggered by CPU utilization
* Add support for customer VPC configurations
* Custom OE VPC if customer VPC not given
* Adding cleanup script
