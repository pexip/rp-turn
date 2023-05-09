# Pexip Reverse Proxy and TURN Server

The administration documentation for this device is available on
[the official Pexip docs site](https://docs.pexip.com/admin/integrate_rpturn.htm).

## Building from source

A general overview for building include; picking an OS base, invoking cloud-init from the virtualization
platform of your choice, and waiting for the virtual machine to boot, configure itself and shut itself down.

Supported and tested base operating systems:

* Ubuntu
    * [22.04 LTS](https://cloud-images.ubuntu.com/jammy/current/)
    * [22.04 LTS (minimal)](https://cloud-images.ubuntu.com/minimal/releases/jammy/release/)
    * [20.04 LTS](https://cloud-images.ubuntu.com/focal/current/)
    * [20.04 LTS (minimal)](https://cloud-images.ubuntu.com/minimal/releases/focal/release/)
* Debian
    * [Bookworm](https://cloud.debian.org/images/cloud/bookworm/daily/latest/)
    * [Bullseye](https://cloud.debian.org/images/cloud/bullseye/daily/latest/)

Each cloud provider/virtualization platform has a unique method of creating a virtual machine and applying configuration
with cloud-init. See the links listed below for specific documentation on this process for platforms we have tested.
Other cloud providers/virtualization platforms may work too but have not yet been tested.

* [VMware vSphere](docs/deploy/vmware-vsphere.md)
* [Google Cloud](docs/deploy/google-cloud.md)
* [Amazon Web Services](docs/deploy/aws.md)
* [Azure](docs/deploy/azure.md)

## Developer guide

This part of the README is for those wishing to customize/improve the Pexip Reverse Proxy/TURN server. There are two
parts to the repo, the Python based installwizard and the Ansible + Cloud-init configuration. Depending on the change,
you may need to look at either one or both sections.

### installwizard Python application

TODO

### Ansible + Cloud-init configuration

TODO
