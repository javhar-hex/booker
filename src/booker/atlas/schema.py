"""
The SQLite schema of an atlas: one row per position, and one per Collider-to-move
position, which the action rows contract.

states: `id`; `key`, the position as `PackedState` bytes, unique; `depth`, the number of
matches played; `active`, the number of live teams, so 1 for a leaf position; `expanded`,
whether its actions have been generated; `gtv`, the game-theoretical value, which is the
minimum guaranteed number of further repeats, once solved.

actions: one per Collider-to-move state up to isomorphism, from the position `parent`.
(lhs, rhs) is the smallest legal pairing of its automorphism orbit, as team indices, and
`class_size` the size of that orbit. The Scheduler pays `repeat_cost`, 1 for a rematch, on
choosing the pairing; `lhs_wins` and `rhs_wins` are the positions that follow each winner. A
Collider state's `gtv` is the larger of its two children's GTVs, and a Scheduler
state's the least, over its actions, of `repeat_cost` + `gtv`.

meta: the game and its GTV convention, the `state_symmetry` implementation, the id of the
root position, and whether the atlas is solved. The schema version is SQLite's own
`PRAGMA user_version`.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from javhar_util.immutables import ZMap

SCHEMA_VERSION = 8

DDL = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS states (
  id INTEGER PRIMARY KEY,
  key BLOB NOT NULL UNIQUE,
  depth INTEGER NOT NULL,
  active INTEGER NOT NULL,
  expanded INTEGER NOT NULL DEFAULT 0 CHECK(expanded IN (0,1)),
  gtv INTEGER,
  CHECK(gtv IS NULL OR gtv >= 0)
);
CREATE INDEX IF NOT EXISTS ix_states_depth ON states(depth,expanded);
CREATE TABLE IF NOT EXISTS actions (
  parent INTEGER NOT NULL REFERENCES states(id),
  lhs INTEGER NOT NULL,
  rhs INTEGER NOT NULL,
  repeat_cost INTEGER NOT NULL CHECK(repeat_cost IN (0,1)),
  class_size INTEGER NOT NULL CHECK(class_size >= 1),
  lhs_wins INTEGER NOT NULL REFERENCES states(id),
  rhs_wins INTEGER NOT NULL REFERENCES states(id),
  gtv INTEGER CHECK(gtv IS NULL OR gtv >= 0),
  PRIMARY KEY(parent,lhs,rhs),
  CHECK(lhs < rhs)
);
CREATE INDEX IF NOT EXISTS ix_actions_lhs_wins ON actions(lhs_wins);
CREATE INDEX IF NOT EXISTS ix_actions_rhs_wins ON actions(rhs_wins);
"""

GAME_META_KEY = "game"
GTV_CONVENTION_META_KEY = "gtv_convention"
ROOT_ID_META_KEY = "root_id"
STATE_SYMMETRY_META_KEY = "state_symmetry"
SOLVED_META_KEY = "solved"
SOLVED_META_VALUE = "true"

META = ZMap(
    {
        GAME_META_KEY: "unrestricted-16-2-6",
        GTV_CONVENTION_META_KEY: "minimum guaranteed additional repeats",
    }
)


def open_connection(path: Path) -> sqlite3.Connection:
    """
    A connection to the database at `path`, which has this schema, created if new. It is in
    autocommit mode: each statement commits itself, and what is done together is done
    between an explicit BEGIN and COMMIT.
    """
    connection = sqlite3.connect(str(path), isolation_level=None)
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA busy_timeout=5000")
    connection.execute("PRAGMA journal_mode=WAL")
    _require_compatible(connection)
    connection.executescript(DDL)
    connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    for key, value in META.items():
        connection.execute(
            "INSERT OR IGNORE INTO meta(key,value) VALUES (?,?)", (key, value)
        )
    return connection


def _require_compatible(connection: sqlite3.Connection) -> None:
    "A database that has tables already must have been written with this schema."
    is_new = connection.execute("SELECT COUNT(*) FROM sqlite_master").fetchone()[0] == 0
    version = connection.execute("PRAGMA user_version").fetchone()[0]
    if not is_new and version != SCHEMA_VERSION:
        raise ValueError(
            f"Database schema v{version} cannot be resumed with schema "
            f"v{SCHEMA_VERSION}; regenerate"
        )
