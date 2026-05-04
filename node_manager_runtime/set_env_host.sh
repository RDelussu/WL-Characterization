#!/bin/bash
curl -sfL https://get.k3s.io | sh
mkdir ~/.kube
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
sudo chown $USER ~/.kube/config
sudo chmod 600 ~/.kube/config 
export KUBECONFIG=~/.kube/config
sudo chmod 644 /etc/rancher/k3s/k3s.yaml
sudo ufw allow 6443/tcp
kubectl get nodes
