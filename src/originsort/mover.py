from __future__ import annotations

import hashlib
import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from .classifier import classify_file
from .storage import MoveRecord, Storage


@dataclass(frozen=True, slots=True)
class MoveResult:
    success: bool
    reason: str
    source: Path
    destination: Path | None = None
    move_id: int | None = None


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def available_destination(path: Path) -> Path:
    if not path.exists():
        return path
    index = 1
    while True:
        candidate = path.with_name(f"{path.stem} ({index}){path.suffix}")
        if not candidate.exists():
            return candidate
        index += 1


def _same_volume(source: Path, destination: Path) -> bool:
    return source.drive.casefold() == destination.drive.casefold()


def _copy_zone_identifier(source: Path, destination: Path) -> None:
    if os.name != "nt":
        return
    try:
        with open(f"{source}:Zone.Identifier", "rb") as src:
            contents = src.read()
        with open(f"{destination}:Zone.Identifier", "wb") as dst:
            dst.write(contents)
    except (FileNotFoundError, OSError):
        return


def _move_verified(source: Path, destination: Path, expected_hash: str) -> None:
    if _same_volume(source, destination):
        source.replace(destination)
        return
    shutil.copy2(source, destination)
    _copy_zone_identifier(source, destination)
    if file_sha256(destination) != expected_hash:
        destination.unlink(missing_ok=True)
        raise OSError("복사된 파일의 내용 검증에 실패했습니다")
    source.unlink()


def move_classified_file(path: Path, storage: Storage,
                         *, execute: bool = False) -> MoveResult:
    classification = classify_file(path, storage)
    source = classification.file_path
    if classification.destination is None:
        return MoveResult(False, classification.reason, source)

    planned = classification.destination
    if source == planned:
        return MoveResult(False, "이미 대상 폴더에 있음", source, planned)
    destination = available_destination(planned)
    if not execute:
        return MoveResult(True, "이동 미리보기", source, destination)

    assert classification.source_key is not None
    expected_hash = file_sha256(source)
    size = source.stat().st_size
    try:
        _move_verified(source, destination, expected_hash)
    except OSError as error:
        return MoveResult(False, f"이동 실패: {error}", source, destination)
    move_id = storage.record_move(source, destination,
                                  classification.source_key,
                                  expected_hash, size)
    return MoveResult(True, "이동 완료", source, destination, move_id)


def undo_move(move_id: int, storage: Storage,
              *, execute: bool = False) -> MoveResult:
    record = storage.get_move(move_id)
    if record is None:
        return MoveResult(False, "이동 기록을 찾을 수 없음", Path("."))
    if record.undone_at is not None:
        return MoveResult(False, "이미 되돌린 이동", record.destination_path,
                          record.source_path, record.id)
    if not record.destination_path.is_file():
        return MoveResult(False, "이동된 파일을 찾을 수 없음",
                          record.destination_path, record.source_path, record.id)
    if record.source_path.exists():
        return MoveResult(False, "원래 위치에 같은 이름의 파일이 있음",
                          record.destination_path, record.source_path, record.id)
    if file_sha256(record.destination_path) != record.sha256:
        return MoveResult(False, "이동 후 파일이 변경되어 되돌릴 수 없음",
                          record.destination_path, record.source_path, record.id)
    if not record.source_path.parent.is_dir():
        return MoveResult(False, "원래 폴더를 찾을 수 없음",
                          record.destination_path, record.source_path, record.id)
    if not execute:
        return MoveResult(True, "되돌리기 미리보기", record.destination_path,
                          record.source_path, record.id)
    try:
        _move_verified(record.destination_path, record.source_path, record.sha256)
    except OSError as error:
        return MoveResult(False, f"되돌리기 실패: {error}",
                          record.destination_path, record.source_path, record.id)
    storage.mark_move_undone(record.id)
    return MoveResult(True, "되돌리기 완료", record.destination_path,
                      record.source_path, record.id)

