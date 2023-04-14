from __future__ import annotations

from invoke import task


@task
def syntax(c):
    """check the syntax of the ansible playbook files"""
    c.run(f"ansible-playbook {c.root_dir}/ansible.yml --syntax-check")


@task(syntax)
def debian_bookworm(c):
    """run ansible inside a container to validate the ansible config"""
    baseimage = "debian:bookworm"
    c.run(f"docker build --build-arg baseimage={baseimage} {c.root_dir}")


@task(syntax)
def debian_bullseye(c):
    """run ansible inside a container to validate the ansible config"""
    baseimage = "debian:bullseye"
    c.run(f"docker build --build-arg baseimage={baseimage} {c.root_dir}")


@task(syntax)
def ubuntu_focal(c):
    """run ansible inside a container to validate the ansible config"""
    baseimage = "ubuntu:20.04"
    c.run(f"docker build --build-arg baseimage={baseimage} {c.root_dir}")


@task(syntax)
def ubuntu_jammy(c):
    """run ansible inside a container to validate the ansible config"""
    baseimage = "ubuntu:22.04"
    c.run(f"docker build --build-arg baseimage={baseimage} {c.root_dir}")


@task(ubuntu_jammy, debian_bookworm, ubuntu_focal, debian_bullseye, default=True)
def all(c):
    pass
