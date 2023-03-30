import hashlib
import json
from functools import wraps
from pathlib import Path
from invoke import task

CHECKSUM_FILE = Path(__file__).parent.parent.absolute() / ".cache" / "invoke.json"


class checksum:
    def __init__(self, *filepaths):
        self._filepaths = filepaths

    @staticmethod
    def _hash_file(file_obj: Path) -> str:
        h = hashlib.sha1()
        h.update(file_obj.read_bytes())
        return h.hexdigest()

    @classmethod
    def check(cls, prefix: str, *filepaths: Path | str) -> bool:
        # load in checksum file
        if not CHECKSUM_FILE.exists():
            return False
        all_checksums = json.loads(CHECKSUM_FILE.read_text())

        # extract out checksum with prefix
        my_checksums = all_checksums.get(prefix)
        if not my_checksums:
            return False

        # iterate all files
        for filepath in filepaths:
            file_obj = Path(filepath) if isinstance(filepath, str) else filepath
            if not file_obj.exists():
                return False
            last_checksum = my_checksums.get(filepath)
            if not last_checksum:
                return False
            if last_checksum != cls._hash_file(file_obj):
                return False

        # all successful
        return True

    @classmethod
    def set(cls, prefix: str, *filepaths: Path | str) -> None:
        all_checksums = (
            json.loads(CHECKSUM_FILE.read_text()) if CHECKSUM_FILE.exists() else {}
        )
        if prefix not in all_checksums:
            all_checksums[prefix] = {}
        my_checksums = all_checksums[prefix]
        for filepath in filepaths:
            file_obj = Path(filepath) if isinstance(filepath, str) else filepath
            my_checksums[str(file_obj)] = cls._hash_file(file_obj)
        CHECKSUM_FILE.write_text(json.dumps(all_checksums))

    def __call__(self, func):
        """Decorator"""

        @wraps(func)
        def inner2(c):
            if self.check(func.__name__, *self._filepaths):
                return
            res = func(c)
            self.set(func.__name__, *self._filepaths)
            return res

        return task(inner2)
