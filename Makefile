bash:
	docker-compose run --rm cdk bash

build:
	docker-compose build

delete:
	docker-compose run -w /code/cdk --rm cdk cdk delete

deploy:
	docker-compose run -w /code/cdk --rm cdk cdk deploy \
	--require-approval never \
	--parameters CertificateArn=arn:aws:acm:us-west-1:992593896645:certificate/9a8d0ee2-9619-45b6-af09-0a78bb813d1a

rebuild:
	docker-compose build --no-cache

synth:
	docker-compose run -w /code/cdk --rm cdk cdk synth
