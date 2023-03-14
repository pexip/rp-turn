# pylint: disable=too-few-public-methods
"""
File writing classes
"""

import os
import shutil
import tempfile
import time


class FileWriter:
    """Generic file writer"""

    def __init__(self, path):
        """Create generic file writer.

        Args:
            - path (str): Absolute path of file to write
        """
        self._path = path

    def write(self, contents: str, mode=0o644, backup=True, suffix="", sync=True):
        """Write data to a file.

        Args:
            - contents (str) : File contents
            - mode     (int) : File access mode
            - backup   (bool): Whether to back up existing file
            - suffix   (str):  Suffix to use for the temporary file
            - sync     (bool): Whether to issue fsync call(s) for extra data safety

        Defaults:
            - mode  : Defaults to a mode of 0644 (rw-r--r--)
            - backup: Defaults to True
            - suffix: Defaults to '' (i.e. no suffix)
            - sync  : Defaults to True
        """
        # Write contents to a temporary file *in the same directory*, so
        # that the rename can be atomic.
        parent_dir = os.path.dirname(os.path.abspath(self._path))
        tmpfile = None
        osfh = None
        try:
            osfh, tmpfile = tempfile.mkstemp(dir=parent_dir, suffix=suffix)
            os.write(osfh, contents.encode("utf-8"))
            if sync:
                os.fsync(osfh)
            os.close(osfh)
            osfh = None

            # Set mode bits
            os.chmod(tmpfile, mode)

            if backup and os.path.exists(self._path):
                # Write backup of existing file
                shutil.copy2(self._path, self._path + ".bak")

            # Atomically replace target
            os.rename(tmpfile, self._path)

        except Exception:
            if tmpfile is not None:
                os.remove(tmpfile)
            if osfh is not None:
                os.close(osfh)
            raise

        # (Optionally) force a sync on the parent directory - if we're
        # being cautious and renaming into place, etc. then let's do
        # our best for data safety by ensuring the file has been
        # updated and is findable in the directory.
        if sync:
            dirfd = os.open(parent_dir, os.O_RDONLY)
            os.fsync(dirfd)
            os.close(dirfd)


class HeadedFileWriter(FileWriter):
    """File writer for headed files."""

    def __init__(self, path):
        """Create headed file writer.

        Args:
            - path (str): Absolute path of file to write
        """
        FileWriter.__init__(self, path)

    def write(self, contents: str, mode=0o644, backup=True, suffix="", sync=True):
        """Write data to a file, prepending a common header.

        Args:
            - contents (str) : File contents
            - mode     (int) : File access mode
            - backup   (bool): Whether to back up existing file
            - suffix   (str):  Suffix to use for the temporary file
            - sync     (bool): Whether to issue fsync call(s) for extra data safety

        Defaults:
            - mode  : Defaults to a mode of 0644 (rw-r--r--)
            - backup: Defaults to True
            - suffix: Defaults to '' (i.e. no suffix)
            - sync  : Defaults to True
        """
        now = time.strftime("%Y-%m-%d %H:%M:%S %Z", time.gmtime())
        heading = f"""# >{self._path}
# Written at {now} by {self.__class__.__name__}
"""
        FileWriter.write(
            self, heading + contents, mode=mode, backup=backup, suffix=suffix, sync=sync
        )
