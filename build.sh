#!/usr/bin/env bash
set -ex

# Cleanup from old run
virsh destroy pexip-rp-turn || /bin/true
virsh undefine pexip-rp-turn --remove-all-storage || /bin/true

# Setup clean disk to use
cp debian-11-generic-amd64.qcow2 disk.qcow2
qemu-img resize disk.qcow2 40G

# Run cloud init
virt-install \
  --name="pexip-rp-turn" \
  --os-variant="ubuntu22.04" \
  --disk="disk.qcow2" \
  --cloud-init "user-data=userdata.yaml" \
  --import

# Compress disk
sudo sudo virt-sparsify disk.qcow2 --compress pexip-rp-turn.qcow2

# Remove vm + uncompressed disk
virsh undefine pexip-rp-turn --remove-all-storage
