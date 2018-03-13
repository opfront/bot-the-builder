#!/bin/bash

# Install Go 1.10
wget https://dl.google.com/go/go1.10.linux-amd64.tar.gz
tar -xvf go1.10.linux-amd64.tar.gz
mv go /usr/local

# Install Google Cloud SDK
echo "deb http://packages.cloud.google.com/apt $CLOUD_SDK_REPO main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add -
apt-get update && apt-get install -y google-cloud-sdk

# Install python dependencies
pip install -r /builder/requirements.txt
