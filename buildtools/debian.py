import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.request import urlretrieve

from invoke import task, call
from yarl import URL

from buildtools.vmbuild import virt_install, virt_sparsify


@task
def download(c, url, name):
    url = URL(url)
    dest = Path(c.download.image_dir) / name
    if dest.exists():
        return dest  # already got the image

    with TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)

        # Get digests
        urlretrieve(str(url.parent / "SHA512SUMS"), tmp / "SHA512SUMS")

        # Get img
        urlretrieve(str(url), tmp / url.name)

        # verify checksum
        with c.cd(tmp):
            c.run(f"sha512sum --check --ignore-missing {tmp}/SHA512SUMS")

        # move to the cache folder
        (tmp / url.name).rename(dest)
    return dest


@task
def bullseye(c, cloud_init=None, no_compress=False):
    image_filename = "debian-bullseye.qcow2"
    download(
        c,
        url="https://cloud.debian.org/images/cloud/bullseye/latest/debian-11-generic-amd64.qcow2",
        name=image_filename,
    )
    build_image = virt_install(c, image_filename=image_filename, cloud_init=cloud_init)
    out_image = c.vmbuild.out_dir / image_filename
    if not no_compress:
        virt_sparsify(c, build_image, out_image)
    else:
        shutil.copy(build_image, out_image)


@task
def bookworm(c, cloud_init=None, compress=True):
    image_filename = "debian-bookworm.qcow2"
    download(
        c,
        url="https://cloud.debian.org/images/cloud/bookworm/daily/latest/debian-12-generic-amd64-daily.qcow2",
        name=image_filename,
    )
    build_image = virt_install(c, image_filename=image_filename, cloud_init=cloud_init)
    out_image = c.vmbuild.out_dir / image_filename
    if compress:
        virt_sparsify(c, build_image, out_image)
    else:
        shutil.copy(build_image, out_image)


@task(bullseye, bookworm, default=True)
def all(c):
    pass
