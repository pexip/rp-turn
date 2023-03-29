import shutil
from pathlib import Path

from invoke import task


@task
def cleanup(c, image_name):
    c.run(f"virsh destroy pexip-rp-turn-{image_name}", warn=True)
    c.run(f"virsh undefine pexip-rp-turn-{image_name} --remove-all-storage", warn=True)


@task
def virt_install(
    c, image_filename: str, cloud_init: str | None = None
):
    cloud_init = Path(cloud_init or "cloud-init/installer")
    image_name = Path(image_filename).stem
    cleanup(c, image_name)

    os_variant = "".join(image_name.split("-")[0:2])
    clean_image = c.download.image_dir / image_filename
    build_image = c.vmbuild.image_dir / image_filename
    user_data = cloud_init / "user-data"
    meta_data = cloud_init / "meta-data"

    shutil.copy(clean_image, build_image)
    c.run(f"qemu-img resize {build_image} 40G")

    c.run(
        " ".join(
            (
                "virt-install",
                f'--name="pexip-rp-turn-{image_name}"',
                f"--os-variant={os_variant}",
                f'--disk="{build_image}"',
                f'--cloud-init "user-data={user_data},meta-data={meta_data}"',
                "--import",
            )
        ),
        pty=True,
    )
    return build_image


@task
def virt_sparsify(c, build_image, out_image):
    c.sudo(f"virt-sparsify {build_image} --compress {out_image}")
