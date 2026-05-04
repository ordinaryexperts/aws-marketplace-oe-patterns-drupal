# Development Guide

For maintainers of the Drupal on AWS by FOSSonCloud pattern.

## Prerequisites

- Docker + Docker Compose
- GNU Make
- AWS profiles `oe-patterns-dev` (account `992593896645`) and `oe-patterns-prod` (account `879777583535`) configured in `~/.aws/`. Profiles are mounted into the devenv container; pass via `AWS_PROFILE=...`.

## Setup

```bash
make update-common   # pulls common.mk from aws-marketplace-utilities (pinned in Makefile)
make build           # builds the devenv Docker image
```

## Common targets

| Target | Description |
|---|---|
| `make synth` | Render the CloudFormation template |
| `make lint` | cfn-lint on the synth output |
| `AWS_PROFILE=oe-patterns-dev make deploy AMI_ID=<id>` | Deploy the dev stack to your `${USER}` namespace in `oe-patterns-dev` |
| `AWS_PROFILE=oe-patterns-dev make destroy` | Tear it down |
| `AWS_PROFILE=oe-patterns-dev make test-integration` | Pytest health checks against the deployed stack |
| `AWS_PROFILE=oe-patterns-dev make test-main` | Taskcat regression in us-east-1 |
| `AWS_PROFILE=oe-patterns-dev make ami-ec2-build TEMPLATE_VERSION=<v>` | Build a dev AMI |
| `AWS_PROFILE=oe-patterns-prod make ami-ec2-build TEMPLATE_VERSION=<v>` | Build the prod AMI for Marketplace ingestion |
| `AWS_PROFILE=oe-patterns-prod make marketplace-validate` | Confirm Marketplace listing metadata is in place |
| `AWS_PROFILE=oe-patterns-dev make publish TEMPLATE_VERSION=<v>` | Publish the CFN template to the public S3 bucket |
| `AWS_PROFILE=oe-patterns-dev make publish-diagram TEMPLATE_VERSION=<v>` | Publish `diagram.png` |
| `AWS_PROFILE=oe-patterns-prod make marketplace-submit AMI_ID=<id> TEMPLATE_VERSION=<v>` | Submit a new version via the Catalog API |
| `AWS_PROFILE=oe-patterns-prod make marketplace-status` | Poll the most recent submission |

## Releasing a new version

The full workflow lives in [`aws-marketplace-utilities/UPGRADE.md`](https://github.com/ordinaryexperts/utilities/UPGRADE.md). Drupal-specific notes:

- Drupal codebase is **baked into the AMI** at `/root/drupal` (composer install during packer). Bumping `DRUPAL_VERSION` in `packer/ubuntu_2404_appinstall.sh` and rebuilding the AMI is what ships a new Drupal version.
- `user_data` writes `sites/default/settings.local.php` on each instance boot (NOT `settings.php` — pre-populating `$databases` in `settings.php` breaks `Drupal\Core\Site\SettingsEditor::rewrite()` during install). The pattern integration code lives in `cdk/drupal/app_launch_config_user_data.sh`.
- The PDO MYSQL_ATTR_SSL_CA index in `settings.local.php` is hardcoded to `1009` (the integer value of the constant) — Drupal core's settings parser can't navigate constant expressions as array indices.
- Marketplace listing uses `marketplace_config.yaml` + the Catalog API. The legacy `plf_config.yaml` flow has been removed.

## Files updated each release

1. `packer/ubuntu_2404_appinstall.sh` — `DRUPAL_VERSION` (and `SCRIPT_VERSION` on devenv major bumps)
2. `cdk/drupal/drupal_stack.py` — `AMI_ID` constant + comment
3. `Makefile` `deploy` target — only if you change the AMI parameter name (e.g. `AsgAmiIdv300` → `AsgAmiIdv310` for next release)
4. `cdk/setup.py` — when bumping `aws-cdk-lib` or `oe-patterns-cdk-common`
5. `CHANGELOG.md`
6. Git tag with the new pattern version (after Marketplace submission `SUCCEEDED`)
