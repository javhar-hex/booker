"""SQLite schema; action rows contract the implicit Collider-to-move nodes.

One action row per Collider-to-move state up to isomorphism: (a,b) is the smallest
legal pairing of its automorphism orbit, class_size the size of that orbit. The
Scheduler pays repeat_cost on choosing the pairing, so a Collider state's value is the
max of its two children's values, and a Scheduler state's value is the min over its
Collider children of repeat_cost + value.
"""
from __future__ import annotations
import sqlite3
from pathlib import Path
from .state import State, pack, unpack

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


def connect(path: str | Path) -> sqlite3.Connection:
    con = sqlite3.connect(str(path))
    con.execute("PRAGMA foreign_keys=ON")
    con.execute("PRAGMA busy_timeout=5000")
    return con


def init(con: sqlite3.Connection):
    row = con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='meta'").fetchone()
    if row:
        previous = con.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
        if previous and previous[0] != '5':
            raise ValueError(f"Database schema v{previous[0]} cannot be resumed with schema v5; regenerate")
    con.executescript(DDL)
    values = {"schema_version":"5", "game":"unrestricted-16-2-6",
              "value_convention":"minimum guaranteed additional repeats"}
    for k,v in values.items():
        con.execute("INSERT OR IGNORE INTO meta(key,value) VALUES (?,?)",(k,v))
    con.commit()


def add_state(con: sqlite3.Connection, s: State) -> int:
    key = pack(s)
    con.execute("INSERT OR IGNORE INTO states(key,depth,active) VALUES (?,?,?)",
                (key,s.depth,len(s.players)))
    return con.execute("SELECT id FROM states WHERE key=?",(key,)).fetchone()[0]


def state_by_id(con: sqlite3.Connection, sid: int) -> State:
    row = con.execute("SELECT key FROM states WHERE id=?",(sid,)).fetchone()
    assert row is not None
    return unpack(row[0])
