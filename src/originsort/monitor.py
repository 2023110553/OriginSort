from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .mover import MoveResult, move_classified_file
from .storage import Storage

TEMPORARY_SUFFIXES = {".crdownload", ".part", ".partial", ".tmp", ".download"}


@dataclass(slots=True)
class PendingFile:
    signature: tuple[int, int]
    stable_checks: int = 0
    attempts: int = 0


class DownloadMonitor:
    def __init__(self, folder: Path, storage: Storage, *, execute: bool = False,
                 stable_checks: int = 2, max_attempts: int = 5,
                 on_result: Callable[[MoveResult], None] | None = None) -> None:
        self.folder = folder.expanduser().resolve()
        self.storage = storage
        self.execute = execute
        self.required_stable_checks = stable_checks
        self.max_attempts = max_attempts
        self.on_result = on_result
        self.pending: dict[Path, PendingFile] = {}
        self.processed: dict[Path, tuple[int, int]] = {}

    @staticmethod
    def _signature(path: Path) -> tuple[int, int]:
        stat = path.stat()
        return stat.st_size, stat.st_mtime_ns

    @staticmethod
    def _eligible(path: Path) -> bool:
        return path.is_file() and path.suffix.casefold() not in TEMPORARY_SUFFIXES

    def remember_existing_files(self) -> None:
        for path in self.folder.iterdir():
            if self._eligible(path):
                try:
                    self.processed[path] = self._signature(path)
                except OSError:
                    continue

    def scan_once(self) -> list[MoveResult]:
        results: list[MoveResult] = []
        current_paths: set[Path] = set()
        for path in self.folder.iterdir():
            if not self._eligible(path):
                continue
            current_paths.add(path)
            try:
                signature = self._signature(path)
            except OSError:
                continue
            if self.processed.get(path) == signature:
                continue
            pending = self.pending.get(path)
            if pending is None or pending.signature != signature:
                self.pending[path] = PendingFile(signature)
                continue
            pending.stable_checks += 1
            if pending.stable_checks < self.required_stable_checks:
                continue
            result = move_classified_file(path, self.storage, execute=self.execute)
            pending.attempts += 1
            results.append(result)
            if self.on_result:
                self.on_result(result)
            moved = self.execute and result.success and result.reason == "이동 완료"
            retryable = result.reason in {
                "지원되는 eClass 출처 정보 없음",
                "파일을 찾을 수 없음",
            }
            if moved:
                self.pending.pop(path, None)
            elif not retryable or pending.attempts >= self.max_attempts:
                self.processed[path] = signature
                self.pending.pop(path, None)
        for stale in set(self.pending) - current_paths:
            self.pending.pop(stale, None)
        return results

    def run(self, interval: float = 1.0) -> None:
        if not self.folder.is_dir():
            raise NotADirectoryError(self.folder)
        self.remember_existing_files()
        while True:
            self.scan_once()
            time.sleep(interval)

