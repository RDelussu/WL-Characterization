#!/bin/bash
sudo mkdir -p /usr/local/bin

curl -sfL https://get.k3s.io | K3S_URL=https://<IP_MASTER>:6443 K3S_TOKEN=<TOKEN> sh -
