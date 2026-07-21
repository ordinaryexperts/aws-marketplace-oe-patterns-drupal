# Unreleased

- Drupal 11.3.8 -> 11.4.4 (11.4.4 is a security-only release fixing SA-CORE-2026-010/011/012 -- moderately critical XSS and access-check issues; 11.4.2 was initially targeted but Composer's advisory check correctly refused to install it once the advisories were published, so the target was bumped to the patched release. No PHP/MySQL requirement changes -- still PHP 8.3, Aurora MySQL 8.0).
- Versioned AMI parameter bumped `AsgAmiIdv300` -> `AsgAmiIdv310`.
- `uploadprogress` PHP extension now installed via the `php8.3-uploadprogress` apt package instead of PECL -- `pecl.php.net` has a long history of intermittent DNS/SSL/504 instability that was causing AMI build failures.

# 3.0.0

Major rewrite. Shipped as a new AWS Marketplace product (the legacy `51c53b7e-fe92-4899-bdcd-b80ccf03de7c` product was Restricted >90 days and AWS Marketplace doesn't accept new versions on those -- see UPGRADE.md).

**Architecture change: bake-into-AMI, drop the CodePipeline**

The 2.x release shipped a CodePipeline + S3 source bucket + CodeBuild + CodeDeploy chain that pulled a Drupal codebase ZIP from S3 and rolled it out to ASG instances. 3.0.0 ships the Drupal codebase pre-baked into the AMI at `/root/drupal` (composer-installed during packer). On first instance boot, user_data copies it into EFS and Apache symlinks `/var/www/app/drupal -> /mnt/efs/drupal`. Same approach the WordPress pattern has used since the start.

What this drops:

* `SourceArtifactBucket`, `PipelineArtifactBucket`, and the BYO-bucket parameters
* `InitializeDefaultDrupal` + `DefaultDrupalSourceUrl` parameters
* CodePipeline + CodeBuild transform project + CodeDeploy application/group + their IAM roles
* CloudFront distribution + cache-invalidation Lambda (was tied to a CodePipeline finalize stage)
* Initialize-default-drupal Lambda + custom resource

What customers get instead:

* Stack creates -> instance boots -> Drupal install wizard appears at the site URL. No pipeline run required.
* Drupal core / contrib / custom code lives in EFS and survives ASG instance replacement.
* Code edits via the Drupal admin UI, or via SSM Session Manager + drush/composer on an instance.
* AMI rebuilds for security patching swap out the kernel + PHP + Apache; the EFS-resident Drupal codebase is preserved.

**Stack components**

* Drupal 11.3.8 (was 9.4.5) -- composer-installed, baked into the AMI
* Drush 13 -- bundled
* PHP 8.3 (was 7.4)
* Ubuntu 24.04 (was 20.04)
* Aurora MySQL 8.0 with `database_name="drupal"` pre-created (was 5.7, no DB pre-created)
* ElastiCache Memcached 1.6 multi-node (was optional, single-node)
* Apache 2.4 with apcu, uploadprogress, intl, opcache, mbstring, gd, mysql, curl, xml, zip
* `oe-patterns-cdk-common` 4.5.1 (was 3.1.0); now uses `AuroraMysql`, `ElasticacheMemcached`, `DbSecret` constructs
* `aws-cdk-lib` 2.225.0 (was 2.20.0)
* devenv image 2.8.3 (was 2.1.3); pip needs `--break-system-packages`
* Packer uses preinstall + postinstall scripts from `aws-marketplace-utilities` 1.6.0

**Breaking changes for existing 2.x deployments**

* New AWS Marketplace product ID. Existing 2.x subscriptions on the legacy product cannot transition automatically. See [UPGRADE.md](UPGRADE.md).
* No more S3-based deploy pipeline. Customers who used `aws s3 cp my-drupal.zip s3://<source-bucket>/drupal.zip` need a different workflow (drush, SSM session).
* No more CloudFront option in the stack.
* `AsgAmiId` -> `AsgAmiIdv300`.
* `SecretArn` parameter renamed to `DbSecretArn` (now provided by `DbSecret` common construct).
* `ElastiCacheEnable` / `ElastiCacheClusterEngineVersion` parameters removed -- Memcached is now always provisioned (default `cache.t4g.micro` x 2 nodes; Memcached requires >=2 nodes for `cross-az` mode in the common construct).

**New behavior**

* `marketplace_config.yaml` replaces the deprecated `plf_config.yaml`. AWS Marketplace submission is via the Catalog API (`make marketplace-submit` / `make marketplace-status`).
* `database_name="drupal"` is created automatically at Aurora cluster creation; install wizard skips the DB-config step.
* `test/integration/` scaffold added (pytest + boto3 + playwright); `make test-integration` runs basic HTTPS / X-Generator checks.
* `oe-patterns-prod` Marketplace ingestion role is `AWSMarketplaceAMIScanning` (the role with the AWS-managed policy attached).
* Branding aligned to "Drupal on AWS by FOSSonCloud".

**Known limitations**

* Memcached is provisioned at the AWS level but the Drupal `memcache` module is not pre-enabled (would break the install bootstrap). After install, run `drush en memcache -y`, then add `$settings['cache']['default'] = 'cache.backend.memcache';` to `sites/default/settings.local.php`.
* No companion `terraform-aws-marketplace-oe-patterns-drupal` module exists; Terraform users would need a wrapper.

# Unreleased (pre-3.0.0; never released)

* Fixing taskcat tests
* CloudFront: forward Drupal https session cookie to origin
* Increase RDS max_allowed_packet parameter to prevent error during MySQL dump imports

# 2.0.0

* Beefing up cleanup script
* Including full guid in append_stack_uuid
* Switching to common VPC construct from OE CDK repo
* Upgrade CDK to 2.20.0
* Reorganizing DrupalStack class code
* Adding output for SourceArtifactBucketName
* Adding uuid to notification topic name
* Upgrading common VPC construct and fixing ALB subnet/healthcheck
* Tweaking AWS Vault references in DEVELOPMENT.md documentation
* Fixing taskcat / docker failure
* Switching to common ASG construct from OE CDK repo
* Switching to common EFS construct from OE CDK repo
* Upgrading to Ubuntu 20.04
* Adding db backup retention parameter
* Using common Makefile tasks
* Upgrading default Drupal site to 9.4.5
* Tightening IAM roles

# 1.0.1

* Updating packages to address CVE-2021-3177
* Upgrading default Drupal site to 9.2.6

# 1.0.0

* AWS::CloudFormation::Interface and other param fixes
* Pass test buckets for each region
* Update supported regions list
* Pass creds in workflow to run clean script
* Fix test params after rename
* CloudFront fixes
* Remove instance types that aren't supported in all regions
* Bump taskcat version
* Add deployment guide
* Parameter name consistency
* make gen-plf - generates Product Load Form info
* CloudFront cache invalidation
* Switch to Aurora MySQL provisioned instead of serverless
* Add apcu and uploadprogress PECL packages
* Update supported regions and taskcat tests
* Fix CloudFront aliases failing in tests
* Update Drupal 9 information in documentation
* Update environment configurations for Drupal in documentation
* Clean up CFN Logical IDs
* Include version in template metadata
* Source artifact bucket and default Drupal initialization copy option

# 0.3.0

* Schedule nightly workflow to test all scenarios
* Test all resources scenario only in main workflow
* Expand test support into other regions
* Update clean up script to cover all regions
* Renaming make targets

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
* Trimming down allowed instance types

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
