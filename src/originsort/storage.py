from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterator


@dataclass(frozen=True, slots=True)
class Rule:
    source_key: str
    destination: Path
    evidence_count: int
    creation_method: str
    enabled: bool


@dataclass(frozen=True, slots=True)
class MoveRecord:
    id: int
    source_path: Path
    destination_path: Path
    source_key: str
    sha256: str
    size: int
    moved_at: str
    undone_at: str | None


def default_database_path() -> Path:
    override = os.environ.get("ORIGINSORT_DATA_DIR")
    if override:
        return Path(override) / "originsort.db"
    base = os.environ.get("LOCALAPPDATA")
    if base:
        return Path(base) / "OriginSort" / "originsort.db"
    return Path.home() / ".originsort" / "originsort.db"


class Storage:
    def __init__(self, path: Path | None = None) -> None:
        self.path = (path or default_database_path()).expanduser().resolve()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                PRAGMA journal_mode = WAL;
                PRAGMA foreign_keys = ON;

                CREATE TABLE IF NOT EXISTS rules (
                    source_key TEXT PRIMARY KEY,
                    destination TEXT NOT NULL,
                    evidence_count INTEGER NOT NULL DEFAULT 0,
                    creation_method TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS moves (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_path TEXT NOT NULL,
                    destination_path TEXT NOT NULL,
                    source_key TEXT NOT NULL,
                    sha256 TEXT NOT NULL,
                    size INTEGER NOT NULL,
                    moved_at TEXT NOT NULL,
                    undone_at TEXT
                );

                CREATE TABLE IF NOT EXISTS app_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                """
            )

    def save_rule(
        self,
        source_key: str,
        destination: Path,
        *,
        evidence_count: int,
        creation_method: str,
    ) -> Rule:
        now = datetime.now(UTC).isoformat()
        normalized_destination = destination.expanduser().resolve()
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO rules (
                    source_key, destination, evidence_count, creation_method,
                    enabled, created_at, updated_at
                ) VALUES (?, ?, ?, ?, 1, ?, ?)
                ON CONFLICT(source_key) DO UPDATE SET
                    destination = excluded.destination,
                    evidence_count = excluded.evidence_count,
                    creation_method = excluded.creation_method,
                    updated_at = excluded.updated_at
                """,
                (source_key, str(normalized_destination), evidence_count,
                 creation_method, now, now),
            )
        return Rule(source_key, normalized_destination, evidence_count,
                    creation_method, True)

    def get_rule(self, source_key: str) -> Rule | None:
        with self.connect() as connection:
            row = connection.execute(
                """SELECT source_key, destination, evidence_count,
                          creation_method, enabled
                   FROM rules WHERE source_key = ?""",
                (source_key,),
            ).fetchone()
        return self._to_rule(row) if row else None

    def list_rules(self) -> list[Rule]:
        with self.connect() as connection:
            rows = connection.execute(
                """SELECT source_key, destination, evidence_count,
                          creation_method, enabled
                   FROM rules ORDER BY source_key"""
            ).fetchall()
        return [self._to_rule(row) for row in rows]

    def set_rule_enabled(self, source_key: str, enabled: bool) -> bool:
        with self.connect() as connection:
            cursor = connection.execute(
                "UPDATE rules SET enabled = ?, updated_at = ? WHERE source_key = ?",
                (1 if enabled else 0, datetime.now(UTC).isoformat(), source_key),
            )
            return cursor.rowcount > 0

    def delete_rule(self, source_key: str) -> bool:
        with self.connect() as connection:
            cursor = connection.execute(
                "DELETE FROM rules WHERE source_key = ?", (source_key,)
            )
            return cursor.rowcount > 0

    def record_move(self, source_path: Path, destination_path: Path,
                    source_key: str, sha256: str, size: int) -> int:
        moved_at = datetime.now(UTC).isoformat()
        with self.connect() as connection:
            cursor = connection.execute(
                """INSERT INTO moves (
                       source_path, destination_path, source_key, sha256,
                       size, moved_at
                   ) VALUES (?, ?, ?, ?, ?, ?)""",
                (str(source_path), str(destination_path), source_key,
                 sha256, size, moved_at),
            )
            return int(cursor.lastrowid)

    def get_move(self, move_id: int) -> MoveRecord | None:
        with self.connect() as connection:
            row = connection.execute(
                """SELECT id, source_path, destination_path, source_key,
                          sha256, size, moved_at, undone_at
                   FROM moves WHERE id = ?""",
                (move_id,),
            ).fetchone()
        return self._to_move(row) if row else None

    def list_moves(self, limit: int = 20) -> list[MoveRecord]:
        with self.connect() as connection:
            rows = connection.execute(
                """SELECT id, source_path, destination_path, source_key,
                          sha256, size, moved_at, undone_at
                   FROM moves ORDER BY id DESC LIMIT ?""",
                (limit,),
            ).fetchall()
        return [self._to_move(row) for row in rows]

    def mark_move_undone(self, move_id: int) -> None:
        with self.connect() as connection:
            connection.execute(
                "UPDATE moves SET undone_at = ? WHERE id = ?",
                (datetime.now(UTC).isoformat(), move_id),
            )

    def get_setting(self, key: str, default: str | None = None) -> str | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT value FROM app_settings WHERE key = ?", (key,)
            ).fetchone()
        return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        with self.connect() as connection:
            connection.execute(
                """INSERT INTO app_settings (key, value) VALUES (?, ?)
                   ON CONFLICT(key) DO UPDATE SET value = excluded.value""",
                (key, value),
            )

    @staticmethod
    def _to_rule(row: sqlite3.Row) -> Rule:
        return Rule(row["source_key"], Path(row["destination"]),
                    row["evidence_count"], row["creation_method"],
                    bool(row["enabled"]))

    @staticmethod
    def _to_move(row: sqlite3.Row) -> MoveRecord:
        return MoveRecord(
            id=row["id"],
            source_path=Path(row["source_path"]),
            destination_path=Path(row["destination_path"]),
            source_key=row["source_key"],
            sha256=row["sha256"],
            size=row["size"],
            moved_at=row["moved_at"],
            undone_at=row["undone_at"],
        )

