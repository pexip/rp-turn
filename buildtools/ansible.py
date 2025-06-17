from __future__ import annotations

from invoke import task


def docker_build(c, base_image, image_name):
    image_tag_cmd = " "
    if image_name:
        image_tag_cmd = f" --tag {image_name} --load "
    c.run(f"docker buildx build --pull --build-arg baseimage={base_image}{image_tag_cmd}{c.root_dir}")

@task
def syntax(c):
    """check the syntax of the ansible playbook files"""
    c.run(f"ansible-playbook {c.root_dir}/ansible.yml --syntax-check")


@task(syntax)
def debian_bookworm(c, image_name=None):
    """run ansible inside a container to validate the ansible config"""
    docker_build(c, "debian:bookworm", image_name)


@task(syntax)
def ubuntu_noble(c, image_name=None):
    """run ansible inside a container to validate the ansible config"""
    docker_build(c, "ubuntu:22.04", image_name)


@task(ubuntu_noble, debian_bookworm, default=True)
def all(c):
    pass
