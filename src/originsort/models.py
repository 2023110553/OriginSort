from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class DownloadMetadata:
    referrer_url: str | None = None
    host_url: str | None = None


@dataclass(frozen=True, slots=True)
class SourceIdentity:
    parser: str
    kind: str
    resource_id: str
    domain: str

    @property
    def key(self) -> str:
        return f"{self.domain}:{self.kind}:{self.resource_id}"


@dataclass(frozen=True, slots=True)
class Evidence:
    file_path: Path
    destination: Path
    source: SourceIdentity

