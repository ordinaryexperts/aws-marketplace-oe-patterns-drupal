bash:
	docker-compose run -w /code --rm drupal bash

build:
	docker-compose build

deploy:
	docker-compose run -w /code/cdk --rm drupal cdk deploy \
	--require-approval never \
	--parameters CustomerVpcId=vpc-03a07d892863eb332 \
	--parameters CustomerVpcPrivateSubnet1=subnet-0e1fd99b403015443 \
	--parameters CustomerVpcPrivateSubnet2=subnet-091ef4266846685f9 \
	--parameters CustomerVpcPublicSubnet1=subnet-045de8badcb368569 \
	--parameters CustomerVpcPublicSubnet2=subnet-02a7fe692dc72614c \
	--parameters CertificateArn=arn:aws:acm:us-west-1:992593896645:certificate/9a8d0ee2-9619-45b6-af09-0a78bb813d1a \
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
