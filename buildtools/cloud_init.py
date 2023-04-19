from __future__ import annotations
from invoke import task


def user_data_files(cloud_init_source):
    return [
        cloud_init_source / "installer" / "user-data"
    ]


@task
def syntax(c):
    """validate cloud-init user data"""
    for user_data in user_data_files(c.cloud_init.source):
        c.run(f"cloud-init schema --config-file {user_data}")


@task(syntax, default=True)
def all(c):
    pass
