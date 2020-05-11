bash:
	docker-compose run -w /code --rm drupal bash

bootstrap:
	docker-compose run -w /code/cdk --rm drupal cdk bootstrap aws://992593896645/us-east-1

build:
	docker-compose build

deploy:
	docker-compose run -w /code/cdk --rm drupal cdk deploy oe-patterns-drupal-helenkim \
	--require-approval never \
	--parameters CertificateArn=arn:aws:acm:us-east-1:992593896645:certificate/77ba53df-8613-4620-8b45-3d22940059d4 \
	--parameters CloudFrontCertificateArn=arn:aws:acm:us-east-1:992593896645:certificate/77ba53df-8613-4620-8b45-3d22940059d4 \
	--parameters SourceArtifactS3ObjectKey=aws-marketplace-oe-patterns-drupal-example-site/refs/heads/feature/DP-43--codedeploy-integration.tar.gz \
	--parameters CustomerVpcId=vpc-00425deda4c835455 \
	--parameters CustomerVpcPrivateSubnet1=subnet-030c94b9795c6cb96 \
	--parameters CustomerVpcPrivateSubnet2=subnet-079290412ce63c4d5 \
	--parameters CustomerVpcPublicSubnet1=subnet-0c2f5d4daa1792c8d \
	--parameters CustomerVpcPublicSubnet2=subnet-060c39a6ded9e89d7

destroy:
	docker-compose run -w /code/cdk --rm drupal cdk destroy

diff:
	docker-compose run -w /code/cdk --rm drupal cdk diff

lint:
	docker-compose run -w /code --rm drupal bash -c "cd cdk \
	&& cdk synth > ../test/template.yaml \
	&& cd ../test \
	&& taskcat lint"

packer:
	docker-compose run -w /code/packer drupal packer build ami.json
.PHONY: packer

rebuild:
	docker-compose build --no-cache

synth:
	docker-compose run -w /code/cdk --rm drupal cdk synth \
	--version-reporting false \
	--path-metadata false \
	--asset-metadata false

synth-drupal-stack:
	docker-compose run -w /code/cdk --rm drupal cdk synth oe-patterns-drupal-helenkim \
	--version-reporting false \
	--path-metadata false \
	--asset-metadata false

synth-vpc-stack:
	docker-compose run -w /code/cdk --rm drupal cdk synth oe-patterns-vpc-helenkim \
	--version-reporting false \
	--path-metadata false \
	--asset-metadata false

test:
	docker-compose run -w /code --rm drupal bash -c "cd cdk \
	&& cdk synth > ../test/template.yaml \
	&& cd ../test \
	&& taskcat test run"
.PHONY: test
