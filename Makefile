ami-docker-bash: ami-docker-build
	docker-compose run --rm ami bash

ami-docker-build:
	docker-compose build ami

ami-docker-rebuild:
	docker-compose build --no-cache ami

ami-ec2-build:
	docker-compose run -w /code --rm drupal bash ./scripts/packer.sh

ami-ec2-copy:
	docker-compose run -w /code --rm drupal bash ./scripts/copy-image.sh $(AMI_ID)

bash:
	docker-compose run -w /code --rm drupal bash

bootstrap:
	docker-compose run -w /code/cdk --rm drupal cdk bootstrap aws://992593896645/us-east-1

build:
	docker-compose build drupal

clean:
	docker-compose run -w /code --rm drupal bash ./scripts/cleanup.sh

clean-all-tcat:
	docker-compose run -w /code --rm drupal bash ./scripts/cleanup.sh all tcat

clean-all-tcat-all-regions:
	docker-compose run -w /code --rm drupal bash ./scripts/cleanup.sh all tcat all

clean-buckets:
	docker-compose run -w /code --rm drupal bash ./scripts/cleanup.sh buckets

clean-buckets-tcat:
	docker-compose run -w /code --rm drupal bash ./scripts/cleanup.sh buckets tcat

clean-buckets-tcat-all-regions:
	docker-compose run -w /code --rm drupal bash ./scripts/cleanup.sh buckets tcat all

clean-logs:
	docker-compose run -w /code --rm drupal bash ./scripts/cleanup.sh logs

clean-logs-tcat:
	docker-compose run -w /code --rm drupal bash ./scripts/cleanup.sh logs tcat

clean-logs-tcat-all-regions:
	docker-compose run -w /code --rm drupal bash ./scripts/cleanup.sh logs tcat all

clean-snapshots:
	docker-compose run -w /code --rm drupal bash ./scripts/cleanup.sh snapshots

clean-snapshots-tcat:
	docker-compose run -w /code --rm drupal bash ./scripts/cleanup.sh snapshots tcat

clean-snapshots-tcat-all-regions:
	docker-compose run -w /code --rm drupal bash ./scripts/cleanup.sh snapshots tcat all

deploy:
	docker-compose run -w /code/cdk --rm drupal cdk deploy \
	--require-approval never \
	--parameters CertificateArn=arn:aws:acm:us-east-1:992593896645:certificate/77ba53df-8613-4620-8b45-3d22940059d4 \
	--parameters CloudFrontCertificateArn=arn:aws:acm:us-east-1:992593896645:certificate/77ba53df-8613-4620-8b45-3d22940059d4 \
	--parameters CloudFrontAliases=cdn-oe-patterns-drupal-${USER}.dev.patterns.ordinaryexperts.com \
	--parameters CloudFrontEnable=true \
	--parameters ElastiCacheEnable=true \
	--parameters DBSnapshotIdentifier=arn:aws:rds:us-east-1:992593896645:snapshot:oe-patterns-drupal-default-20200610 \
	--parameters PipelineArtifactBucketName=github-user-and-bucket-taskcatbucket-2zppaw3wi3sx \
	--parameters SecretArn=arn:aws:secretsmanager:us-east-1:992593896645:secret:/test/drupal/rds-instance/secret-HXBSLp \
	--parameters SourceArtifactS3ObjectKey=aws-marketplace-oe-patterns-drupal-example-site/refs/heads/feature/DP-97--drupal-upgrade.zip \
	--parameters VpcId=vpc-00425deda4c835455 \
	--parameters VpcPrivateSubnetId1=subnet-030c94b9795c6cb96 \
	--parameters VpcPrivateSubnetId2=subnet-079290412ce63c4d5 \
	--parameters VpcPublicSubnetId1=subnet-0c2f5d4daa1792c8d \
	--parameters VpcPublicSubnetId2=subnet-060c39a6ded9e89d7

destroy:
	docker-compose run -w /code/cdk --rm drupal cdk destroy

diff:
	docker-compose run -w /code/cdk --rm drupal cdk diff

gen-plf:
	docker-compose run -w /code --rm drupal python3 ./scripts/gen-plf.py

lint:
	docker-compose run -w /code --rm drupal bash ./scripts/lint.sh

publish:
	docker-compose run -w /code --rm drupal bash ./scripts/publish-template.sh

rebuild:
	docker-compose build --no-cache drupal

synth:
	docker-compose run -w /code/cdk --rm drupal cdk synth \
	--version-reporting false \
	--path-metadata false \
	--asset-metadata false

synth-to-file:
	docker-compose run -w /code --rm drupal bash -c "cd cdk \
	&& cdk synth \
	--version-reporting false \
	--path-metadata false \
	--asset-metadata false > /code/dist/template.yaml \
	&& echo 'Template saved to dist/template.yaml'"

test-all:
	docker-compose run -w /code --rm drupal bash -c "cd cdk \
	&& cdk synth > ../test/template.yaml \
	&& cd ../test \
	&& taskcat test run"

test-main:
	docker-compose run -w /code --rm drupal bash -c "cd cdk \
	&& cdk synth > ../test/main-test/template.yaml \
	&& cd ../test/main-test \
	&& taskcat test run"
