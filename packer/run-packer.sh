#!/usr/bin/env bash

aws-vault exec oe-patterns-dev -- packer build ami.json
