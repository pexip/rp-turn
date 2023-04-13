from __future__ import annotations
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.request import urlretrieve

from invoke import task
from yarl import URL

from buildtools.vmbuild import virt_install, virt_sparsify


@task
def fetch_gpg_keys(c):
    key_ids = (
        "4A3CE3CD565D7EB5C810E2B97FF3F408476CF100",
        "D2EB44626FDDC30B513D5BB71A5D6C4C7DB87C81",
    )
    for key_id in key_ids:
        status = c.run(f"gpg --list-keys {key_id}", warn=True)
        if status.exited:
            # need to fetch key
            c.run(
                f"gpg --keyid-format long --keyserver hkp://keyserver.ubuntu.com --recv-keys {key_id}"
            )


@task(fetch_gpg_keys)
def download(c, url, name, minimal):
    url = URL(url)
    dest = Path(c.download.image_dir) / name
    if dest.exists():
        return  # already got the image

    with TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)

        # Get gpg digests
        urlretrieve(str(url.parent / "SHA256SUMS.gpg"), tmp / "SHA256SUMS.gpg")
        if minimal:
            # inline signature
            c.run(f"gpg --decrypt {tmp}/SHA256SUMS.gpg > {tmp}/SHA256SUMS")
        else:
            # detached signature
            urlretrieve(str(url.parent / "SHA256SUMS"), tmp / "SHA256SUMS")
            c.run(f"gpg --verify {tmp}/SHA256SUMS.gpg {tmp}/SHA256SUMS")

        # Get img
        urlretrieve(str(url), tmp / url.name)

        # verify checksum
        c.run(f"cd {tmp} && sha256sum --check --ignore-missing {tmp}/SHA256SUMS")

        # move to the cache folder
        (tmp / url.name).rename(dest)


@task
def jammy(c, cloud_init=None, no_compress=False):
    image_filename = "ubuntu-jammy.img"
    download(
        c,
        url="https://cloud-images.ubuntu.com/jammy/current/jammy-server-cloudimg-amd64.img",
        name=image_filename,
        minimal=False,
    )
    build_image = virt_install(c, image_filename=image_filename, cloud_init=cloud_init)
    out_image = c.vmbuild.out_dir / image_filename
    if not no_compress:
        virt_sparsify(c, build_image, out_image)
    else:
        shutil.copy(build_image, out_image)


@task
def jammy_minimal(c, cloud_init=None, no_compress=False):
    image_filename = "ubuntu-jammy-minimal.img"
    download(
        c,
        url="https://cloud-images.ubuntu.com/minimal/releases/jammy/release/ubuntu-22.04-minimal-cloudimg-amd64.img",
        name=image_filename,
        minimal=True,
    )
    build_image = virt_install(c, image_filename=image_filename, cloud_init=cloud_init)
    out_image = c.vmbuild.out_dir / image_filename
    if not no_compress:
        virt_sparsify(c, build_image, out_image)
    else:
        shutil.copy(build_image, out_image)


@task
def focal(c, cloud_init=None, no_compress=False):
    image_filename = "ubuntu-focal.img"
    download(
        c,
        url="https://cloud-images.ubuntu.com/focal/current/focal-server-cloudimg-amd64.img",
        name=image_filename,
        minimal=False,
    )
    build_image = virt_install(c, image_filename=image_filename, cloud_init=cloud_init)
    out_image = c.vmbuild.out_dir / image_filename
    if not no_compress:
        virt_sparsify(c, build_image, out_image)
    else:
        shutil.copy(build_image, out_image)


@task
def focal_minimal(c, cloud_init=None, no_compress=False):
    image_filename = "ubuntu-focal-minimal.img"
    download(
        c,
        url="https://cloud-images.ubuntu.com/minimal/releases/focal/release/ubuntu-20.04-minimal-cloudimg-amd64.img",
        name=image_filename,
        minimal=True,
    )
    build_image = virt_install(c, image_filename=image_filename, cloud_init=cloud_init)
    out_image = c.vmbuild.out_dir / image_filename
    if not no_compress:
        virt_sparsify(c, build_image, out_image)
    else:
        shutil.copy(build_image, out_image)


@task(jammy, jammy_minimal, focal, focal_minimal, default=True)
def all(c):
    pass
