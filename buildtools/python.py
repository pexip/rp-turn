from __future__ import annotations
from invoke import task

from buildtools.utils import checksum


@checksum("pyproject.toml", "poetry.lock")
def setup_env(c):
    c.run("poetry install --sync")


@task(setup_env)
def isort(c, source=None, check=False):
    source = source or c.python.source
    check_str = "--check-only " if check else ""
    result = c.run(f"poetry run isort {check_str}{source}")
    print(result)


@task(setup_env)
def black(c, source=None, check=False):
    source = source or c.python.source
    check_str = "--check " if check else ""
    c.run(f"poetry run black {check_str}{source}")


@task(setup_env)
def mypy(c, source=None):
    source = source or c.python.source
    c.run(f"poetry run mypy {source}")


@task(setup_env)
def pylint(c, source=None):
    source = source or c.python.source
    c.run(f"poetry run pylint {source}")


@task(setup_env)
def pytest(c, source=None):
    source = source or c.python.source
    c.run(f"poetry run pytest {source}")


@task(isort, black, mypy, pylint, pytest, default=True)
def all(c):
    pass
