bash:
	docker-compose run -w /code --rm drupal bash

build:
	docker-compose build

deploy:
	docker-compose run -w /code/cdk --rm drupal cdk deploy \
	--require-approval never \
	--parameters CertificateArn=arn:aws:acm:us-west-1:992593896645:certificate/9a8d0ee2-9619-45b6-af09-0a78bb813d1a

destroy:
	docker-compose run -w /code/cdk --rm drupal cdk destroy

packer:
	docker-compose run -w /code/packer drupal packer build ami.json
.PHONY: packer

rebuild:
	docker-compose build --no-cache

synth:
	docker-compose run -w /code/cdk --rm drupal cdk synth
