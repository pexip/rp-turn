#!/usr/bin/env bash
set -ex

# Cleanup from old run
virsh destroy pexip-rp-turn || /bin/true
virsh undefine pexip-rp-turn --remove-all-storage || /bin/true

# Setup clean disk to use
cp jammy-server-cloudimg-amd64.img disk.img
qemu-img resize disk.img 40G

# Run cloud init
virt-install \
  --name="pexip-rp-turn" \
  --os-variant="ubuntu22.04" \
  --disk="disk.img" \
  --cloud-init "user-data=userdata.yaml" \
  --import
