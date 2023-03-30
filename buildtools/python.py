from invoke import task

from buildtools.utils import checksum


@checksum("pyproject.toml", "poetry.lock")
def setup_env(c):
    c.run("poetry install --sync")


@task(setup_env)
def isort(c, source=None):
    source = source or c.python.source
    result = c.run(f"poetry run isort {source}")
    print(result)


@task(setup_env)
def black(c, source=None):
    source = source or c.python.source
    c.run(f"poetry run black {source}")


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
