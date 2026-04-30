# Upgrading from 2.x to 3.0.0

The 3.0.0 release is a major rewrite. **You cannot update a 2.x stack in place** — Aurora MySQL has been bumped from 5.7 to 8.0 (different engine versions), the CFN logical IDs across the database stack changed when the pattern moved to the `AuroraMysql` common construct, and several CloudFormation parameters were renamed. Treat 3.0.0 as a new product and migrate via snapshot-restore.

## Migration steps

1. **Take a final snapshot of your 2.x Aurora cluster.**
   ```bash
   aws rds create-db-cluster-snapshot \
     --db-cluster-snapshot-identifier my-2x-final-snapshot \
     --db-cluster-identifier <your-2x-cluster-id>
   ```
   Wait until the snapshot is `available` before continuing.

2. **(Optional) Tear down the 2.x stack.** If you want to release the running resources first, delete it now. The snapshot is independent of the stack.

3. **Deploy 3.0.0 with `DbSnapshotIdentifier` set.** In the CloudFormation console (or via `aws cloudformation create-stack`) deploy the new template, supplying:
   - `DbSnapshotIdentifier=arn:aws:rds:<region>:<account>:cluster-snapshot:my-2x-final-snapshot`
   - `DbSecretArn=<your existing secret ARN>` — required when restoring from snapshot, since the snapshot's master password is whatever you set in 2.x. Pre-populate the secret with `username` and `password` keys matching the snapshot.
   - `InitializeDefaultDrupal=false` — you don't want to overwrite your codebase with the demo site.
   - `SourceArtifactBucketName=<your existing bucket>` if you want to keep using the same S3 bucket for code deploys.

4. **Wait for `CREATE_COMPLETE`.** Aurora MySQL upgrades the snapshot from 5.7 to 8.0 in place during the restore. ~15–20 min.

5. **Sync EFS data.** The new stack creates a fresh EFS. Mount both the old and new EFS to a temporary EC2 instance (or use AWS DataSync) and copy `sites/default/files` across:
   ```bash
   sudo rsync -av /mnt/old-efs/drupal/files/ /mnt/new-efs/drupal/files/
   sudo chown -R www-data:www-data /mnt/new-efs/drupal/files
   ```

6. **Build a Drupal 11–compatible codebase.** Drupal 9 modules don't run on Drupal 11. You must:
   - Update your codebase locally: `composer require drupal/core-recommended:^11 ...`
   - Resolve any contrib-module incompatibilities (modules with no D11 release will need to be replaced or removed).
   - Test locally against a copy of your snapshot.

7. **Push the new codebase.** Upload your D11 codebase ZIP to the source bucket key `drupal.zip`. CodePipeline auto-detects the new object and rolls out via CodeDeploy.
   ```bash
   aws s3 cp my-d11-drupal.zip s3://<source-bucket>/drupal.zip
   ```

8. **Run Drupal's database update path.** SSH (Session Manager) into an EC2 instance and run the Drupal core updates 9 → 10 → 11 in order:
   ```bash
   cd /var/www/app/drupal
   sudo -u www-data ./vendor/bin/drush updatedb -y
   sudo -u www-data ./vendor/bin/drush cache:rebuild
   ```
   You may need to step through this in two phases (D9 → D10, then D10 → D11) depending on how your codebase is structured.

9. **(Optional) Re-enable memcache caching.** The Drupal `memcache` module is not pre-enabled in 3.0.0 (it would break the install bootstrap). To wire up the cluster:
   ```bash
   sudo -u www-data ./vendor/bin/drush en memcache -y
   ```
   Then add to `sites/default/settings.local.php`:
   ```php
   $settings['cache']['default'] = 'cache.backend.memcache';
   ```

10. **Switch DNS.** Once the new stack is healthy, update your customer-facing DNS / Route53 record to point at the new ALB (the 3.0.0 stack creates a new ALB; the old hostname is unchanged but the ALB target ARN is new).

11. **Tear down the 2.x stack** if you haven't already.

## Parameter rename map

| 2.x parameter | 3.0.0 parameter | Notes |
|---|---|---|
| `AsgAmiId` | `AsgAmiIdv300` | Versioned per release |
| `SecretArn` | `DbSecretArn` | Now provided by `DbSecret` common construct |
| `ElastiCacheEnable` | *(removed)* | Memcached now always provisioned |
| `ElastiCacheClusterEngineVersion` | *(removed)* | Pinned by common construct (1.6.6) |
| `ElastiCacheClusterCacheNodeType` | unchanged | Defaults to `cache.t4g.micro` |
| `ElastiCacheClusterNumCacheNodes` | unchanged | Default bumped to 2 |
| `DbBackupRetentionPeriod` | `DbBackupRetentionPeriod` | Same name, now under `Db` namespace in common construct |
| `DbInstanceClass` | `DbInstanceClass` | Same name, now provided by `AuroraMysql` |
| `DbSnapshotIdentifier` | `DbSnapshotIdentifier` | Same |

## Known limitations

- The `drupal/cdn` contrib module was dropped from the bundled example-site (constraint conflict against D11.3.8). If you depended on its `CloudFrontDistributionEndpointOutput`-driven URL substitution, you'll need to re-add it to your composer.json or implement the URL substitution in your theme/preprocess hooks.
- No companion `terraform-aws-marketplace-oe-patterns-drupal` Terraform module exists yet. CloudFormation only.
