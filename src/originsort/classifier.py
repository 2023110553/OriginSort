from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .scanner import inspect_file
from .storage import Rule, Storage


@dataclass(frozen=True, slots=True)
class Classification:
    file_path: Path
    source_key: str | None
    rule: Rule | None
    reason: str

    @property
    def destination(self) -> Path | None:
        return self.rule.destination / self.file_path.name if self.rule else None


def classify_file(path: Path, storage: Storage) -> Classification:
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        return Classification(resolved, None, None, "파일을 찾을 수 없음")
    evidence = inspect_file(resolved)
    if evidence is None:
        return Classification(resolved, None, None, "지원되는 eClass 출처 정보 없음")
    source_key = evidence.source.key
    rule = storage.get_rule(source_key)
    if rule is None:
        return Classification(resolved, source_key, None, "등록된 규칙 없음")
    if not rule.enabled:
        return Classification(resolved, source_key, None, "규칙이 비활성화됨")
    if not rule.destination.is_dir():
        return Classification(resolved, source_key, None, "대상 폴더를 찾을 수 없음")
    return Classification(resolved, source_key, rule, "분류 가능")

