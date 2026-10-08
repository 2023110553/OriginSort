from __future__ import annotations

from configparser import ConfigParser
from pathlib import Path

from .models import DownloadMetadata


def read_zone_identifier(path: Path) -> DownloadMetadata | None:
    """Read Windows' Zone.Identifier alternate data stream without changing the file."""
    stream_path = f"{path}:Zone.Identifier"
    try:
        with open(stream_path, "r", encoding="utf-8-sig") as stream:
            raw = stream.read()
    except (FileNotFoundError, OSError, UnicodeError):
        return None

    parser = ConfigParser(interpolation=None)
    try:
        parser.read_string(raw)
    except Exception:
        return None

    if not parser.has_section("ZoneTransfer"):
        return None

    section = parser["ZoneTransfer"]
    return DownloadMetadata(
        referrer_url=section.get("ReferrerUrl"),
        host_url=section.get("HostUrl"),
    )

