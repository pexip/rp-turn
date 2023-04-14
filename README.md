# Pexip Reverse Proxy and TURN Server

The usage documentation for this device is on the official pexip docs
site: https://docs.pexip.com/admin/integrate_rpturn.htm

## Building from source

The general steps required for building involve picking an OS to base from, invoking cloud-init on the virtualization
platform of your choice, and waiting for the virtual machine to shut itself down.

Supported base operating systems:

* Ubuntu
    * [22.04 LTS](https://cloud-images.ubuntu.com/jammy/current/)
    * [22.04 LTS (minimal)](https://cloud-images.ubuntu.com/minimal/releases/jammy/release/)
    * [20.04 LTS](https://cloud-images.ubuntu.com/focal/current/)
    * [20.04 LTS (minimal)](https://cloud-images.ubuntu.com/minimal/releases/focal/release/)
* Debian
    * [Bookworm](https://cloud.debian.org/images/cloud/bookworm/daily/latest/)
    * [Bullseye](https://cloud.debian.org/images/cloud/bullseye/daily/latest/)

Each virtualization platform has a different way to create the virtual machine and configure it with cloud-init. The
platforms listed below are linked to more specific documentation on how to do this. Other virtualization platforms may
work too.

* [VMware vSphere](docs/deploy/vmware-vsphere.md)
* [Google Cloud](docs/deploy/google-cloud.md)
* [Amazon Web Services](docs/deploy/aws.md)
* [Azure](docs/deploy/azure.md)

## Developer guide

This part of the README is for those wishing to customize/improve the Pexip Reverse Proxy/TURN server. There are two
parts to the repo, the python based installwizard and the Ansible + Cloud-init configuration. Depending on the change,
you may need to look at either one or both sections.

### installwizard python application

TODO

### Ansible + Cloud-init configuration

TODO
