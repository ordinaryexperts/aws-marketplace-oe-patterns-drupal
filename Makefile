-include common.mk

update-common:
	wget -O common.mk https://raw.githubusercontent.com/ordinaryexperts/aws-marketplace-utilities/1.8.0/common.mk

deploy: build
	docker compose run -w /code/cdk --rm devenv cdk deploy \
	--require-approval never \
	--parameters AlbCertificateArn=arn:aws:acm:us-east-1:992593896645:certificate/943928d7-bfce-469c-b1bf-11561024580e \
	--parameters AlbIngressCidr=0.0.0.0/0 \
	--parameters AsgAmiIdv300=$(AMI_ID) \
	--parameters AsgReprovisionString=$(shell date +%Y%m%d.%H%M%S) \
	--parameters DnsHostname=drupal-${USER}.dev.patterns.ordinaryexperts.com \
	--parameters DnsRoute53HostedZoneName=dev.patterns.ordinaryexperts.com

# Integration testing targets
test-integration: build
	docker compose run -w /code/test/integration --rm devenv bash -c "pip install -q -r requirements.txt --break-system-packages && pytest test_health.py -v"

test-integration-all: build
	docker compose run -w /code/test/integration --rm devenv bash -c "pip install -q -r requirements.txt --break-system-packages && pytest -v"
