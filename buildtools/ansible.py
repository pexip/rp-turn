from __future__ import annotations

from invoke import task


@task
def syntax(c):
    c.run(f"ansible-playbook {c.root_dir}/ansible.yml --syntax-check")


@task(syntax, default=True)
def all(c):
    pass
