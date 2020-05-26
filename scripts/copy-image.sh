#!/usr/bin/env bash

if [ "$#" -ne 1 ]; then
    echo "Usage: make AMI_ID=ami-xxxxxxxxx copy-image"
    exit
fi
AMI_ID=$1

AMI_NAME=`aws ec2 describe-images --image-ids $AMI_ID | jq -r '.Images[].Name'`

supported_regions=(
    "us-east-2"
    "us-west-1"
    "us-west-2"
)

mapping_code="# AMI list generated by:\n"
mapping_code+="# make AMI_ID=$AMI_ID copy-image\n"
mapping_code+="# on $(date).\n"
mapping_code+="generated_ami_ids = {\n"

for i in ${!supported_regions[@]}; do
    region=${supported_regions[$i]}
    echo -n "Checking $region..."
    copied_ami_id=`AWS_REGION=$region aws ec2 describe-images --filters Name=name,Values=$AMI_NAME | jq -r '.Images[].ImageId'`
    if [[ -z "${copied_ami_id}" ]]; then
        echo -n "need to copy AMI..."
        copied_ami_id=`AWS_REGION=$region aws ec2 copy-image --name $AMI_NAME --source-image-id $AMI_ID --source-region us-east-1 | jq -r '.ImageId'`
        echo "done."
    else
        echo "AMI already copied."
    fi
    mapping_code+="    \"$region\": \"$copied_ami_id\",\n"
done
mapping_code+="    \"us-east-1\": \"$AMI_ID\"\n"
mapping_code+="}\n# End generated code block.\n\n"
echo "All done copying image!"
echo -e "Copy the below code into drupal_stack.py where indicated:\n"
echo -e "$mapping_code"
