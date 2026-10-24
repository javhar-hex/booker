"""Equilibrium pass over a solved atlas, written to a separate database.

The atlas is attached read-only; results are keyed by its state ids and Collider rows:

- equilibrium: reachable from the root when both players only make optimal moves.
- critical (Collider positions): an equilibrium position where one winner is a mistake.
- fewest_past_repeats: the fewest repeats over all paths from the root. A position is
  balanced when this plus its value equals the root value; off the equilibrium path,
  that means it is only reachable through mistakes that cancel each other out.
"""

from __future__ import annotations

import argparse
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from util.dtypes.immutables.z_vec import ZVec

SCHEMA = """
CREATE TABLE scheduler_flags (
  id INTEGER PRIMARY KEY,
  equilibrium INTEGER NOT NULL CHECK(equilibrium IN (0, 1)),
  fewest_past_repeats INTEGER NOT NULL CHECK(fewest_past_repeats >= 0)
);
CREATE TABLE collider_flags (
  parent INTEGER NOT NULL,
  a INTEGER NOT NULL,
  b INTEGER NOT NULL,
  equilibrium INTEGER NOT NULL CHECK(equilibrium IN (0, 1)),
  critical INTEGER NOT NULL CHECK(critical IN (0, 1) AND critical <= equilibrium),
  fewest_past_repeats INTEGER NOT NULL CHECK(fewest_past_repeats >= 0),
  PRIMARY KEY(parent, a, b)
);
"""

COLLIDER_LAYER = """
WITH layer AS (
  SELECT c.parent, c.a, c.b,
         f.equilibrium AND c.repeat_cost + c.value = p.value AS optimal_pairing,
         MIN(wa.value, wb.value) < c.value AS has_mistake,
         f.fewest_past_repeats + c.repeat_cost AS repeats
  FROM atlas.states p
  JOIN atlas.actions c ON c.parent = p.id
  JOIN scheduler_flags f ON f.id = p.id
  JOIN atlas.states wa ON wa.id = c.a_wins
  JOIN atlas.states wb ON wb.id = c.b_wins
  WHERE p.depth = ?
)
INSERT INTO collider_flags
SELECT parent, a, b, optimal_pairing, optimal_pairing AND has_mistake, repeats FROM layer
"""

SCHEDULER_LAYER = """
WITH edge AS (
  SELECT CASE w.side WHEN 0 THEN c.a_wins ELSE c.b_wins END AS child,
         f.equilibrium, c.value AS collider_value, f.fewest_past_repeats
  FROM atlas.states p
  JOIN atlas.actions c ON c.parent = p.id
  JOIN collider_flags f ON (f.parent, f.a, f.b) = (c.parent, c.a, c.b)
  CROSS JOIN (SELECT 0 AS side UNION ALL SELECT 1) w
  WHERE p.depth = ?
)
INSERT INTO scheduler_flags
SELECT e.child, MAX(e.equilibrium AND s.value = e.collider_value),
       MIN(e.fewest_past_repeats)
FROM edge e JOIN atlas.states s ON s.id = e.child
GROUP BY e.child
"""


@dataclass(frozen=True)
class LayerSummary:
    depth: int
    scheduler: int
    scheduler_equilibrium: int
    scheduler_balanced_off_equilibrium: int
    collider: int
    collider_equilibrium: int
    collider_critical: int


SUMMARY = """
WITH s AS (
  SELECT st.depth, COUNT(*) AS n, SUM(f.equilibrium) AS eq,
         SUM(NOT f.equilibrium AND f.fewest_past_repeats + st.value = ?) AS balanced_off
  FROM atlas.states st JOIN scheduler_flags f ON f.id = st.id GROUP BY st.depth
), c AS (
  SELECT p.depth, COUNT(*) AS n, SUM(f.equilibrium) AS eq, SUM(f.critical) AS critical
  FROM collider_flags f JOIN atlas.states p ON p.id = f.parent GROUP BY p.depth
)
SELECT s.depth, s.n, s.eq, s.balanced_off,
       COALESCE(c.n, 0), COALESCE(c.eq, 0), COALESCE(c.critical, 0)
FROM s LEFT JOIN c ON c.depth = s.depth ORDER BY s.depth
"""


def build(atlas: Path, out: Path) -> None:
    if out.exists():
        raise FileExistsError(out)
    con = _attached(atlas, out)
    _require_solved(con)
    con.executescript(SCHEMA)
    with con:
        con.execute("INSERT INTO scheduler_flags VALUES (?, 1, 0)", (_root_id(con),))
        for depth in range(_max_depth(con)):
            con.execute(COLLIDER_LAYER, (depth,))
            con.execute(SCHEDULER_LAYER, (depth,))
    _require_every_state_flagged(con)
    con.close()


def summary(atlas: Path, flags: Path) -> ZVec[LayerSummary]:
    con = _attached(atlas, flags)
    rows = con.execute(SUMMARY, (_root_value(con),)).fetchall()
    con.close()
    return ZVec(
        LayerSummary(
            depth=depth,
            scheduler=scheduler,
            scheduler_equilibrium=scheduler_equilibrium,
            scheduler_balanced_off_equilibrium=balanced_off,
            collider=collider,
            collider_equilibrium=collider_equilibrium,
            collider_critical=collider_critical,
        )
        for (
            depth,
            scheduler,
            scheduler_equilibrium,
            balanced_off,
            collider,
            collider_equilibrium,
            collider_critical,
        ) in rows
    )


def _attached(atlas: Path, flags: Path) -> sqlite3.Connection:
    con = sqlite3.connect(flags)
    con.execute("ATTACH DATABASE ? AS atlas", (f"file:{atlas}?mode=ro",))
    return con


def _root_id(con: sqlite3.Connection) -> int:
    row = con.execute("SELECT value FROM atlas.meta WHERE key = 'root_id'").fetchone()
    return int(row[0])


def _root_value(con: sqlite3.Connection) -> int:
    row = con.execute("SELECT value FROM atlas.states WHERE id = ?", (_root_id(con),))
    return int(row.fetchone()[0])


def _max_depth(con: sqlite3.Connection) -> int:
    return int(con.execute("SELECT MAX(depth) FROM atlas.states").fetchone()[0])


def _require_solved(con: sqlite3.Connection) -> None:
    unsolved = con.execute(
        "SELECT (SELECT COUNT(*) FROM atlas.states WHERE value IS NULL)"
        " + (SELECT COUNT(*) FROM atlas.actions WHERE value IS NULL)"
    ).fetchone()[0]
    if unsolved:
        raise ValueError(f"Atlas is not solved: {unsolved:,} positions without a value")


def _require_every_state_flagged(con: sqlite3.Connection) -> None:
    missing = con.execute(
        "SELECT COUNT(*) FROM atlas.states s"
        " WHERE NOT EXISTS (SELECT 1 FROM scheduler_flags f WHERE f.id = s.id)"
    ).fetchone()[0]
    if missing:
        raise RuntimeError(f"{missing:,} states were never reached from the root")


def main() -> None:
    parser = argparse.ArgumentParser(description="Equilibrium pass over a solved atlas")
    parser.add_argument("atlas", type=Path)
    parser.add_argument("flags", type=Path)
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args()
    if not args.summary_only:
        build(args.atlas, args.flags)
    for layer in summary(args.atlas, args.flags):
        print(layer)


if __name__ == "__main__":
    main()
