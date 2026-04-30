# Unreleased

# 3.0.0

Major rewrite to bring the pattern current after a 3.5-year hiatus.

**Stack components**

* Drupal 11.3.8 (was 9.4.5)
* PHP 8.3 (was 7.4)
* Ubuntu 24.04 (was 20.04)
* Aurora MySQL 8.0 (was 5.7)
* ElastiCache Memcached 1.6 (was 1.5.16)
* Apache 2.4 with apcu, uploadprogress, intl, opcache, mbstring, gd, mysql, curl, xml, zip
* `oe-patterns-cdk-common` 4.5.1 (was 3.1.0); now uses `AuroraMysql`, `ElasticacheMemcached`, `DbSecret` constructs
* `aws-cdk-lib` 2.225.0 (was 2.20.0)
* devenv image 2.8.3 (was 2.1.3); requires `--break-system-packages` for pip
* Packer pulls preinstall + postinstall scripts from `aws-marketplace-utilities` `1.6.0`

**Breaking changes for existing 2.x deployments**

The 3.0.0 stack has a different parameter surface and a different Aurora major version. **An existing 2.x stack cannot be updated in place to 3.0.0.** Treat 3.0.0 as a new product and follow [UPGRADE.md](UPGRADE.md) to migrate.

* Pattern version triggers a versioned AMI parameter rename: `AsgAmiId` → `AsgAmiIdv300`.
* `SecretArn` parameter renamed to `DbSecretArn` (now provided by `DbSecret` common construct).
* `ElastiCacheEnable` / `ElastiCacheClusterEngineVersion` parameters removed — Memcached is now always provisioned (default `cache.t4g.micro` × 2 nodes; Memcached requires ≥2 nodes for `cross-az` mode in the common construct).
* `AuroraMysql` common construct replaces hand-rolled Aurora resources. New CFN logical IDs across the database stack.
* The default Drupal codebase is now Drupal 11. Existing customers who installed via Drupal install wizard on 2.0.0 will need to dump their D9 database, restore into the new D9-snapshot-based 2.x stack, run Drupal core update path 9 → 10 → 11, and re-deploy.

**New behavior**

* `marketplace_config.yaml` replaces the deprecated `plf_config.yaml`. AWS Marketplace submission is now via the Catalog API (`make marketplace-submit` / `make marketplace-status`) rather than the old PLF/spreadsheet flow.
* New `DefaultDrupalSourceUrl` parameter — customers can supply their own Drupal codebase ZIP at stack creation time.
* `InitializeDefaultDrupal=true` now seeds an out-of-box Drupal 11 codebase from `aws-marketplace-oe-patterns-drupal-example-site` 2.0.0.
* `database_name="drupal"` is created automatically at Aurora cluster creation; install wizard skips the DB-config step.
* `test/integration/` scaffold added (pytest + boto3 + playwright); `make test-integration` runs basic health/HTTPS/`X-Generator` checks against the deployed stack.
* `oe-patterns-prod` Marketplace ingestion role is `AWSMarketplaceAMIScanning` (the role with the AWS-managed policy attached).
* Branding aligned to "Drupal on AWS by FOSSonCloud".

**Known limitations**

* Memcached is enabled at the AWS level by default but the Drupal `memcache` module is not pre-enabled (would otherwise break the install bootstrap). Customers run `drush en memcache -y`, then add `$settings['cache']['default'] = 'cache.backend.memcache';` to `sites/default/settings.local.php` to wire it up.
* `drupal/cdn` contrib module dropped from the example-site (had a constraint conflict against D11.3.8); CloudFront integration is partial. Customers who want explicit CDN URL substitution can re-add the module via composer.
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
