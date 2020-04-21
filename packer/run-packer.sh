#!/usr/bin/env bash

aws-vault exec oe-prod -- packer build ami.json
