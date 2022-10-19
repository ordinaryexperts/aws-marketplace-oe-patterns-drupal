-include common.mk

update-common:
	wget -O common.mk https://raw.githubusercontent.com/ordinaryexperts/aws-marketplace-utilities/1.1.0/common.mk

deploy: build
	docker-compose run -w /code/cdk --rm devenv cdk deploy \
	--require-approval never \
	--parameters AlbCertificateArn=arn:aws:acm:us-east-1:992593896645:certificate/943928d7-bfce-469c-b1bf-11561024580e \
	--parameters AlbIngressCidr=0.0.0.0/0 \
	--parameters AsgReprovisionString=20220903.1 \
	--parameters CloudFrontCertificateArn=arn:aws:acm:us-east-1:992593896645:certificate/943928d7-bfce-469c-b1bf-11561024580e \
	--parameters CloudFrontAliases=cdn-oe-patterns-drupal-${USER}.dev.patterns.ordinaryexperts.com \
	--parameters CloudFrontEnable=false \
	--parameters DnsHostname=drupal-${USER}.dev.patterns.ordinaryexperts.com \
	--parameters DnsRoute53HostedZoneName=dev.patterns.ordinaryexperts.com \
	--parameters ElastiCacheEnable=false \
	--parameters InitializeDefaultDrupal=true \
	--parameters PipelineArtifactBucketName=github-user-and-bucket-taskcatbucket-2zppaw3wi3sx \
	--parameters SecretArn=arn:aws:secretsmanager:us-east-1:992593896645:secret:/test/drupal/secret-P6y46J \
	--parameters SourceArtifactBucketName=github-user-and-bucket-githubartifactbucket-wl52dae3lyub \
	--parameters SourceArtifactObjectKey=aws-marketplace-oe-patterns-drupal-example-site/dev/20220903.1.zip \
	--parameters VpcId=vpc-00425deda4c835455 \
	--parameters VpcPrivateSubnet1Id=subnet-030c94b9795c6cb96 \
	--parameters VpcPrivateSubnet2Id=subnet-079290412ce63c4d5 \
	--parameters VpcPublicSubnet1Id=subnet-0c2f5d4daa1792c8d \
	--parameters VpcPublicSubnet2Id=subnet-060c39a6ded9e89d7
