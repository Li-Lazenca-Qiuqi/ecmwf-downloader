"""YAML 文件的同目录原子替换与跨进程写锁。"""

import os
import tempfile
from contextlib import contextmanager
from pathlib import Path

import yaml


@contextmanager
def file_write_lock(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.with_name(path.name + '.lock').open('a+b') as handle:
        if os.name == 'nt':
            import msvcrt

            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        # 文件关闭时释放锁；锁文件独立于被替换的目标文件。
        yield


def atomic_write_yaml(path: Path, data: dict) -> None:
    content = yaml.safe_dump(data, allow_unicode=True, sort_keys=False).encode("utf-8")
    atomic_write_bytes(path, content)


def atomic_write_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f'.{path.name}.', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)
