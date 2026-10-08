from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from .metadata import read_zone_identifier
from .models import Evidence
from .parsers import parse_eclass_source


@dataclass(frozen=True, slots=True)
class RuleCandidate:
    source_key: str
    destinations: dict[Path, int]

    @property
    def status(self) -> str:
        return "확정 후보" if len(self.destinations) == 1 else "충돌"

    @property
    def evidence_count(self) -> int:
        return sum(self.destinations.values())


def inspect_file(path: Path) -> Evidence | None:
    metadata = read_zone_identifier(path)
    if metadata is None:
        return None

    source = parse_eclass_source(metadata.referrer_url)
    if source is None:
        source = parse_eclass_source(metadata.host_url)
    if source is None:
        return None

    return Evidence(file_path=path, destination=path.parent, source=source)


def scan_folder(root: Path) -> tuple[list[RuleCandidate], int]:
    grouped: dict[str, dict[Path, int]] = defaultdict(lambda: defaultdict(int))
    inspected = 0

    for path in root.rglob("*"):
        if not path.is_file():
            continue
        inspected += 1
        evidence = inspect_file(path)
        if evidence is not None:
            grouped[evidence.source.key][evidence.destination] += 1

    candidates = [
        RuleCandidate(source_key=key, destinations=dict(destinations))
        for key, destinations in sorted(grouped.items())
    ]
    return candidates, inspected

