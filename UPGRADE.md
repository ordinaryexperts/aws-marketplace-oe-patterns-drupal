# Upgrading from 2.x to 3.0.0

3.0.0 ships as a **new AWS Marketplace product** with a different product ID. The legacy 2.x product (`51c53b7e-fe92-4899-bdcd-b80ccf03de7c`) was Restricted in AWS Marketplace for >90 days, and AWS Marketplace doesn't accept new versions on products in that state.

It's also a major architecture change. 2.x ran a CodePipeline → CodeBuild → CodeDeploy chain that pulled a Drupal codebase ZIP from S3 and rolled it out to ASG instances. 3.0.0 bakes the Drupal codebase into the AMI and copies it to EFS on first boot. The pipeline + S3 source bucket are gone.

There is **no in-place upgrade path** between the two products. You'll deploy the new product as a parallel stack, migrate data and code, then DNS-cut over.

## Migration steps

1. **Subscribe to the new product** in AWS Marketplace ("Drupal on AWS by FOSSonCloud") and accept its terms. (URL will be sent out when the new product is live.)

2. **Take a final snapshot of your 2.x Aurora cluster.**
   ```bash
   aws rds create-db-cluster-snapshot \
     --db-cluster-snapshot-identifier my-2x-final-snapshot \
     --db-cluster-identifier <your-2x-cluster-id>
   ```
   Wait until the snapshot is `available` before continuing.

3. **Deploy 3.0.0 with `DbSnapshotIdentifier` set.** In the CloudFormation console (or via `aws cloudformation create-stack`) deploy the new template, supplying:
   - `DbSnapshotIdentifier=arn:aws:rds:<region>:<account>:cluster-snapshot:my-2x-final-snapshot`
   - `DbSecretArn=<your existing secret ARN>` -- required when restoring from snapshot, since the snapshot's master password is whatever you set in 2.x. Pre-populate the secret with `username` and `password` keys matching the snapshot.
   - `DnsHostname` and `DnsRoute53HostedZoneName` for a *new* hostname (e.g. `drupal-new.example.com`) — you'll cut over DNS at the end.

4. **Wait for `CREATE_COMPLETE`.** Aurora MySQL upgrades the snapshot from 5.7 to 8.0 in place during the restore. ~15-20 min. The 3.0.0 stack's first instance will boot, copy the AMI's `/root/drupal` (Drupal 11.3.8 codebase) into a fresh EFS filesystem, and start Apache. Visiting the new hostname will show the **Drupal install wizard** with the database fields pre-populated to point at the restored DB.

5. **Stop. Don't run the install wizard yet.** Your snapshot has a Drupal 9 schema. Running the 3.0.0 install wizard would create new tables and conflict with what's there. Instead, you need to upgrade the schema in place.

6. **Sync `sites/default/files` from old EFS to new EFS.** Spin up a tiny EC2 instance, mount both EFS filesystems, and copy the user-uploaded media:
   ```bash
   sudo rsync -av /mnt/old-efs/drupal/files/ /mnt/new-efs/drupal/sites/default/files/
   sudo chown -R www-data:www-data /mnt/new-efs/drupal/sites/default/files
   ```
   (In 2.x the path was `/mnt/efs/drupal/files`. In 3.0.0 the codebase lives in EFS too, so the path is `/mnt/efs/drupal/sites/default/files`.)

7. **Replace the new stack's Drupal codebase with your D11-upgraded codebase.** Two paths:

   **Path A — upgrade in place using your existing customizations:**
   - SSM-session into a 3.0.0 instance.
   - Backup the AMI-baked codebase: `sudo mv /mnt/efs/drupal /mnt/efs/drupal-amibase`
   - Copy your 2.x Drupal 9 codebase from your old EFS (or git clone your existing project) into `/mnt/efs/drupal/`
   - Update its `composer.json` to D11: `composer require drupal/core-recommended:^11 ...`
   - Resolve any contrib-module incompatibilities locally first (modules with no D11 release will need replacement or removal).
   - Copy the pattern-integration block from `/mnt/efs/drupal-amibase/sites/default/settings.php` (the bottom block that reads `/opt/oe/patterns/drupal/*.json`) into your codebase's settings.php.

   **Path B — start with the AMI-baked Drupal 11 and import only your data:**
   - Leave `/mnt/efs/drupal` as the AMI default.
   - Don't run the Drupal install wizard.
   - SSM-session in, then: `cd /var/www/app/drupal && sudo -u www-data ./vendor/bin/drush updatedb -y`
   - This runs the D9 → D11 schema migrations against your restored data.
   - Then re-enable any contrib modules you depended on: `sudo -u www-data ./vendor/bin/drush en <module> -y`

8. **Run `drush updatedb` and `drush cache:rebuild`** to apply schema and clear caches:
   ```bash
   cd /var/www/app/drupal
   sudo -u www-data ./vendor/bin/drush updatedb -y
   sudo -u www-data ./vendor/bin/drush cache:rebuild
   ```

9. **(Optional) Enable Memcached caching.** The Drupal `memcache` module is bundled but not enabled (would break the install bootstrap if it were):
   ```bash
   sudo -u www-data ./vendor/bin/drush en memcache -y
   ```
   Then add to `sites/default/settings.local.php`:
   ```php
   $settings['cache']['default'] = 'cache.backend.memcache';
   ```

10. **Smoke-test on the new hostname.** Browse the site, log in, post content, verify file uploads land on the new EFS.

11. **Switch DNS.** Update your customer-facing Route53 record to point at the new ALB. The DNS propagates within minutes; the old ALB then serves no traffic.

12. **Tear down the 2.x stack.** Once you've confirmed the new stack handles production for a few days.

## Parameter rename map

| 2.x parameter | 3.0.0 parameter | Notes |
|---|---|---|
| `AsgAmiId` | `AsgAmiIdv300` | Versioned per release |
| `SecretArn` | `DbSecretArn` | Now provided by `DbSecret` common construct |
| `SourceArtifactBucketName` | *(removed)* | No more S3-source pipeline |
| `SourceArtifactObjectKey` | *(removed)* | No more S3-source pipeline |
| `PipelineArtifactBucketName` | *(removed)* | No more CodePipeline |
| `InitializeDefaultDrupal` | *(removed)* | Drupal codebase is baked into the AMI |
| `DefaultDrupalSourceUrl` | *(removed)* | Drupal codebase is baked into the AMI |
| `CloudFrontEnable`/`CloudFrontAliases`/`CloudFrontCertificateArn`/`CloudFrontPriceClass` | *(removed)* | CloudFront dropped from the stack |
| `ElastiCacheEnable` | *(removed)* | Memcached now always provisioned |
| `ElastiCacheClusterEngineVersion` | *(removed)* | Pinned by common construct (1.6.6) |
| `ElastiCacheClusterCacheNodeType` | unchanged | Defaults to `cache.t4g.micro` |
| `ElastiCacheClusterNumCacheNodes` | unchanged | Default bumped to 2 |
| `DbBackupRetentionPeriod` | unchanged | Now under `Db` namespace in common construct |
| `DbInstanceClass` | unchanged | Now provided by `AuroraMysql` |
| `DbSnapshotIdentifier` | unchanged | Same |

## Customer deploy workflow change

In 2.x, the canonical way to deploy code to your fleet was:
```bash
aws s3 cp my-drupal.zip s3://<source-bucket>/drupal.zip
# CodePipeline auto-detects, runs CodeBuild + CodeDeploy
```

In 3.0.0, code lives in EFS. Options:

- **Drupal admin UI** — install/update modules and themes via the Extend page (writes to EFS).
- **SSM Session Manager + drush** — SSH-equivalent into an instance, then `cd /var/www/app/drupal && sudo -u www-data ./vendor/bin/drush ...`
- **SSM Session Manager + composer** — `sudo -u www-data composer require drupal/<module>` writes to EFS.
- **Custom downstream automation** — wire your own Lambda or CodeBuild that does `git pull` + `composer install` over an EFS mount.

## Why the architecture changed

- **Eliminates 4 distinct failure modes** we saw under the pipeline approach: source-bucket seed lambda blank URL, drush wrapper permission, PHP 8 strict-constant in settings.php, memcache module chicken-and-egg with cache backend setting.
- **Self-contained AMI** for first deploy — no external repo dependency.
- **Faster first-boot** — no pipeline wait time. Stack creates → Apache serves Drupal in one step.
- **Matches the WordPress pattern's architecture**, which has shipped this way successfully since launch.
- **AMI rebuilds for security patching are decoupled** from customer code — the EFS-resident codebase survives ASG instance replacement.

## Known limitations

- No companion `terraform-aws-marketplace-oe-patterns-drupal` module exists. CloudFormation only.
