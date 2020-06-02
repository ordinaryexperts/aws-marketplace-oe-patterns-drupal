#!/usr/bin/env bash

# https://stackoverflow.com/a/246128
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

VERSION=`git describe` packer build $DIR/../packer/ami.json
