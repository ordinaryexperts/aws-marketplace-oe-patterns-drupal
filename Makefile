bash:
	docker-compose run -w /code --rm drupal bash

bootstrap:
	docker-compose run -w /code/cdk --rm drupal cdk bootstrap aws://992593896645/us-east-1

build:
	docker-compose build

deploy:
	docker-compose run -w /code/cdk --rm drupal cdk deploy \
	--require-approval never \
	--parameters CertificateArn=arn:aws:acm:us-east-1:992593896645:certificate/77ba53df-8613-4620-8b45-3d22940059d4 \
	--parameters CloudFrontCertificateArn=arn:aws:acm:us-east-1:992593896645:certificate/77ba53df-8613-4620-8b45-3d22940059d4

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

test:
	docker-compose run -w /code --rm drupal bash -c "cd cdk \
	&& cdk synth > ../test/template.yaml \
	&& cd ../test \
	&& taskcat test run"
.PHONY: test
