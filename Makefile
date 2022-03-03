-include common.mk

update-common:
	wget -O common.mk https://raw.githubusercontent.com/ordinaryexperts/aws-marketplace-utilities/feature/common-scripts/common.mk

deploy: build
	docker-compose run -w /code/cdk --rm devenv cdk deploy \
	--require-approval never \
	--parameters CertificateArn=arn:aws:acm:us-east-1:992593896645:certificate/943928d7-bfce-469c-b1bf-11561024580e \
	--parameters CloudFrontCertificateArn=arn:aws:acm:us-east-1:992593896645:certificate/943928d7-bfce-469c-b1bf-11561024580e \
	--parameters CloudFrontAliases=cdn-oe-patterns-drupal-${USER}.dev.patterns.ordinaryexperts.com \
	--parameters CloudFrontEnable=false \
	--parameters ElastiCacheEnable=false \
	--parameters InitializeDefaultDrupal=true \
	--parameters PipelineArtifactBucketName=github-user-and-bucket-taskcatbucket-2zppaw3wi3sx \
	--parameters SecretArn=arn:aws:secretsmanager:us-east-1:992593896645:secret:/test/drupal/secret-P6y46J \
	--parameters SourceArtifactBucketName=github-user-and-bucket-githubartifactbucket-wl52dae3lyub \
	--parameters SourceArtifactObjectKey=aws-marketplace-oe-patterns-drupal-example-site/refs/heads/develop.zip \
	--parameters VpcId=vpc-00425deda4c835455 \
	--parameters VpcPrivateSubnetId1=subnet-030c94b9795c6cb96 \
	--parameters VpcPrivateSubnetId2=subnet-079290412ce63c4d5 \
	--parameters VpcPublicSubnetId1=subnet-0c2f5d4daa1792c8d \
	--parameters VpcPublicSubnetId2=subnet-060c39a6ded9e89d7
