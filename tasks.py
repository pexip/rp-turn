import os
from pathlib import Path

from invoke import Collection

from buildtools import ansible, cloud_init, dev, debian, ubuntu, python, vmbuild

root = Path(__file__).parent.absolute()
image_cache = root / ".cache" / "images"

python_src = root / "src"
os.makedirs(python_src, exist_ok=True)

cloud_init_src = root / "cloud-init"

download_image_dir = image_cache / "clean"
os.makedirs(download_image_dir, exist_ok=True)

vmbuild_image_dir = image_cache / "build"
vmbuild_out_dir = root
os.makedirs(vmbuild_image_dir, exist_ok=True)
os.makedirs(vmbuild_out_dir, exist_ok=True)

namespace = Collection(ansible, cloud_init, dev, debian, ubuntu, python, vmbuild)
namespace.configure(
    {
        "python": {"source": python_src},
        "download": {"image_dir": download_image_dir},
        "vmbuild": {"image_dir": vmbuild_image_dir, "out_dir": vmbuild_out_dir},
        "cloud_init": {"source": cloud_init_src},
        "git_dir": root / ".git",
        "root_dir": root,
        "run": {"echo": True},
    }
)
