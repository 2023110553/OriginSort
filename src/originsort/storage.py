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


def default_database_path() -> Path:
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

    @staticmethod
    def _to_rule(row: sqlite3.Row) -> Rule:
        return Rule(row["source_key"], Path(row["destination"]),
                    row["evidence_count"], row["creation_method"],
                    bool(row["enabled"]))

