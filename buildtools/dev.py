import stat
from functools import partial
from pathlib import Path

from invoke import task
from http import server


@task
def git_hooks(c):
    script = """\
#!/bin/sh
#
# An example hook script to prepare a packed repository for use over
# dumb transports.
#
# To enable this hook, rename this file to "post-update".

exec git update-server-info
"""
    for hook_name in ["post-commit", "post-update"]:
        hook_path: Path = c.git_dir / "hooks" / hook_name
        hook_path.write_text(script)
        hook_path.chmod(
            stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH
        )


@task(git_hooks)
def git_server(c, address="", port=8000):
    """
    Run the git repo as a local http server for the vmbuild to pickup
    """
    c.run("git update-server-info")
    http = server.HTTPServer(
        (address, port), partial(server.SimpleHTTPRequestHandler, directory=c.root_dir)
    )
    print(f"running http server on {address}:{port}")
    http.serve_forever()
