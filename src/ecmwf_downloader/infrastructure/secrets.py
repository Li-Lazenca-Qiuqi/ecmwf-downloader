"""Permission-checked YAML secret storage for local-only deployments."""

from __future__ import annotations

import copy
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Optional

import yaml


class SecretStore:
    """Store CDS and AI credentials in a separate 0600 YAML file.

    The lock is a sibling file so an atomic ``os.replace`` cannot invalidate
    another process' lock while the Web process and CLI edit accounts.
    """

    def __init__(self, path: Path):
        self.path = Path(path)
        self.lock_path = self.path.with_name(self.path.name + ".lock")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._atomic_write({"version": 1, "accounts": [], "ai": {}})
        self._ensure_permissions()

    def _ensure_permissions(self) -> None:
        try:
            os.chmod(self.path, 0o600)
            if self.lock_path.exists():
                os.chmod(self.lock_path, 0o600)
        except OSError:
            # Windows development environments may not support POSIX modes.
            pass

    @contextmanager
    def _lock(self, exclusive: bool = False) -> Iterator[None]:
        import fcntl

        self.lock_path.touch(exist_ok=True)
        self._ensure_permissions()
        with self.lock_path.open("r+", encoding="utf-8") as lock_handle:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
            try:
                yield
            finally:
                fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)

    def _read_unlocked(self) -> dict[str, Any]:
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                data = yaml.safe_load(handle) or {}
        except FileNotFoundError:
            data = {"version": 1, "accounts": [], "ai": {}}
        if not isinstance(data, dict):
            raise ValueError("secrets.yaml 必须是对象")
        data.setdefault("version", 1)
        data.setdefault("accounts", [])
        data.setdefault("ai", {})
        return data

    def _atomic_write(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=f".{self.path.name}.", dir=self.path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                yaml.safe_dump(data, handle, allow_unicode=True, sort_keys=False)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temp_name, 0o600)
            os.replace(temp_name, self.path)
            self._ensure_permissions()
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)

    def _update(self, callback) -> None:
        with self._lock(exclusive=True):
            data = self._read_unlocked()
            callback(data)
            self._atomic_write(data)

    def snapshot(self) -> dict[str, Any]:
        with self._lock():
            return copy.deepcopy(self._read_unlocked())

    def accounts(self, include_keys: bool = False) -> list[dict[str, Any]]:
        accounts = self.snapshot().get("accounts", [])
        if include_keys:
            return accounts
        return [{key: value for key, value in item.items() if key != "key"} for item in accounts]

    def get_account(self, account_id: str) -> Optional[dict[str, Any]]:
        for account in self.accounts(include_keys=True):
            if account.get("id") == account_id:
                return account
        return None

    def upsert_account(self, account: dict[str, Any]) -> None:
        required = {"id", "email", "key"}
        missing = required - account.keys()
        if missing:
            raise ValueError(f"账号缺少字段: {', '.join(sorted(missing))}")

        def update(data: dict[str, Any]) -> None:
            accounts = data.setdefault("accounts", [])
            for index, existing in enumerate(accounts):
                if existing.get("id") == account["id"]:
                    accounts[index] = {**existing, **account}
                    break
            else:
                accounts.append(account)

        self._update(update)

    def delete_account(self, account_id: str) -> bool:
        removed = False

        def update(data: dict[str, Any]) -> None:
            nonlocal removed
            accounts = data.setdefault("accounts", [])
            kept = [item for item in accounts if item.get("id") != account_id]
            removed = len(kept) != len(accounts)
            data["accounts"] = kept

        self._update(update)
        return removed

    def ai_config(self) -> dict[str, Any]:
        data = self.snapshot().get("ai", {})
        return dict(data) if isinstance(data, dict) else {}

    def update_ai(self, values: dict[str, Any]) -> None:
        def update(data: dict[str, Any]) -> None:
            data["ai"] = {**data.get("ai", {}), **values}

        self._update(update)
