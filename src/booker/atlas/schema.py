"""
The SQLite schema of an atlas: one row per position, and one per Collider-to-move
position, which the action rows contract.

states: `id`; `key`, the position as `PackedState` bytes, unique; `depth`, the number of
matches played; `active`, the number of live teams, so 1 for a decided position; `expanded`,
whether its actions have been generated; `value`, the minimum guaranteed number of further
repeats, once solved.

actions: one per Collider-to-move state up to isomorphism, from the position `parent`.
(a, b) is the smallest legal pairing of its automorphism orbit, as team indices, and
`class_size` the size of that orbit. The Scheduler pays `repeat_cost`, 1 for a rematch, on
choosing the pairing; `a_wins` and `b_wins` are the positions that follow each winner. A
Collider state's `value` is the larger of its two children's values, and a Scheduler
state's the least, over its actions, of `repeat_cost` + `value`.

meta: the schema version and game, the canonicalization backend, the id of the root
position, and whether the atlas is solved.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA_VERSION = "5"

DDL = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS states (
  id INTEGER PRIMARY KEY,
  key BLOB NOT NULL UNIQUE,
  depth INTEGER NOT NULL,
  active INTEGER NOT NULL,
  expanded INTEGER NOT NULL DEFAULT 0 CHECK(expanded IN (0,1)),
  value INTEGER,
  CHECK(value IS NULL OR value >= 0)
);
CREATE INDEX IF NOT EXISTS ix_states_depth ON states(depth,expanded);
CREATE TABLE IF NOT EXISTS actions (
  parent INTEGER NOT NULL REFERENCES states(id),
  a INTEGER NOT NULL,
  b INTEGER NOT NULL,
  repeat_cost INTEGER NOT NULL CHECK(repeat_cost IN (0,1)),
  class_size INTEGER NOT NULL CHECK(class_size >= 1),
  a_wins INTEGER NOT NULL REFERENCES states(id),
  b_wins INTEGER NOT NULL REFERENCES states(id),
  value INTEGER CHECK(value IS NULL OR value >= 0),
  PRIMARY KEY(parent,a,b),
  CHECK(a < b)
);
CREATE INDEX IF NOT EXISTS ix_actions_a ON actions(a_wins);
CREATE INDEX IF NOT EXISTS ix_actions_b ON actions(b_wins);
"""

META = {
    "schema_version": SCHEMA_VERSION,
    "game": "unrestricted-16-2-6",
    "value_convention": "minimum guaranteed additional repeats",
}


def open_connection(path: str | Path) -> sqlite3.Connection:
    "A connection to the database at `path`, which has this schema, created if new."
    con = sqlite3.connect(str(path))
    con.execute("PRAGMA foreign_keys=ON")
    con.execute("PRAGMA busy_timeout=5000")
    con.execute("PRAGMA journal_mode=WAL")
    _require_compatible(con)
    con.executescript(DDL)
    for key, value in META.items():
        con.execute("INSERT OR IGNORE INTO meta(key,value) VALUES (?,?)", (key, value))
    con.commit()
    return con


def _require_compatible(con: sqlite3.Connection) -> None:
    has_meta = con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='meta'"
    ).fetchone()
    if not has_meta:
        return
    previous = con.execute(
        "SELECT value FROM meta WHERE key='schema_version'"
    ).fetchone()
    if previous and previous[0] != SCHEMA_VERSION:
        raise ValueError(
            f"Database schema v{previous[0]} cannot be resumed with schema "
            f"v{SCHEMA_VERSION}; regenerate"
        )
