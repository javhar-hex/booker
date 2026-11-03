"""Equilibrium pass on a hand-built solved atlas whose flags can be read off by hand.

Root R (value 1) has four Collider children (pairing: repeat cost, winners, value):
  C1 (0,1): cost 0, X=1 / Y=0, value 1  -> equilibrium, critical
  C2 (0,2): cost 1, Z=1 / Y=0, value 1  -> off: 1 + 1 > 1
  C3 (0,3): cost 0, W=2 / V=1, value 2  -> off: 0 + 2 > 1
  C4 (1,2): cost 0, X=1 / Z=1, value 1  -> equilibrium, indifferent
V is balanced off the equilibrium path: the Scheduler's C3 and the Collider's V cancel.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

import pytest
from javhar_util.immutables import ZMap, ZVec

from booker.atlas.schema import open_connection
from booker.equilibrium import LayerSummary, build, summary

R, X, Y, Z, W, V = 1, 2, 3, 4, 5, 6
VALUES = ZMap({R: 1, X: 1, Y: 0, Z: 1, W: 2, V: 1})


@dataclass(frozen=True)
class Collider:
    a: int
    b: int
    repeat_cost: int
    a_wins: int
    b_wins: int
    value: int


COLLIDERS = ZVec(
    [
        Collider(a=0, b=1, repeat_cost=0, a_wins=X, b_wins=Y, value=1),
        Collider(a=0, b=2, repeat_cost=1, a_wins=Z, b_wins=Y, value=1),
        Collider(a=0, b=3, repeat_cost=0, a_wins=W, b_wins=V, value=2),
        Collider(a=1, b=2, repeat_cost=0, a_wins=X, b_wins=Z, value=1),
    ]
)


@dataclass(frozen=True)
class Flags:
    equilibrium: bool
    fewest_past_repeats: int


def _tiny_atlas(path: Path) -> Path:
    con = open_connection(path)
    with con:
        con.execute("INSERT INTO meta VALUES ('root_id', ?)", (str(R),))
        for sid, value in VALUES.items():
            depth = 0 if sid == R else 1
            con.execute(
                "INSERT INTO states (id, key, depth, active, expanded, value)"
                " VALUES (?, ?, ?, 2, 1, ?)",
                (sid, bytes([sid]), depth, value),
            )
        for c in COLLIDERS:
            con.execute(
                "INSERT INTO actions (parent, a, b, repeat_cost, class_size, a_wins,"
                " b_wins, value) VALUES (?, ?, ?, ?, 1, ?, ?, ?)",
                (R, c.a, c.b, c.repeat_cost, c.a_wins, c.b_wins, c.value),
            )
    con.close()
    return path


@pytest.fixture
def flagged(tmp_path: Path) -> Path:
    atlas = _tiny_atlas(tmp_path / "atlas.db")
    build(atlas, tmp_path / "flags.db")
    return tmp_path


def _query(flags: Path, sql: str) -> list[tuple[int, ...]]:
    con = sqlite3.connect(flags)
    rows = con.execute(sql).fetchall()
    con.close()
    return rows


def test_scheduler_flags(flagged: Path) -> None:
    rows = _query(flagged / "flags.db", "SELECT * FROM scheduler_flags")
    got = ZMap(
        {
            sid: Flags(equilibrium=bool(eq), fewest_past_repeats=past)
            for sid, eq, past in rows
        }
    )
    assert got == ZMap(
        {
            R: Flags(equilibrium=True, fewest_past_repeats=0),
            X: Flags(equilibrium=True, fewest_past_repeats=0),
            Y: Flags(equilibrium=False, fewest_past_repeats=0),
            Z: Flags(equilibrium=True, fewest_past_repeats=0),
            W: Flags(equilibrium=False, fewest_past_repeats=0),
            V: Flags(equilibrium=False, fewest_past_repeats=0),
        }
    )


def test_collider_flags(flagged: Path) -> None:
    sql = "SELECT a, b, equilibrium, critical, fewest_past_repeats FROM collider_flags"
    assert set(_query(flagged / "flags.db", sql)) == {
        (0, 1, 1, 1, 0),
        (0, 2, 0, 0, 1),
        (0, 3, 0, 0, 0),
        (1, 2, 1, 0, 0),
    }


def test_summary(flagged: Path) -> None:
    layers = summary(flagged / "atlas.db", flagged / "flags.db")
    assert layers == ZVec(
        [
            LayerSummary(
                depth=0,
                scheduler=1,
                scheduler_equilibrium=1,
                scheduler_balanced_off_equilibrium=0,
                collider=4,
                collider_equilibrium=2,
                collider_critical=1,
            ),
            LayerSummary(
                depth=1,
                scheduler=5,
                scheduler_equilibrium=2,
                scheduler_balanced_off_equilibrium=1,
                collider=0,
                collider_equilibrium=0,
                collider_critical=0,
            ),
        ]
    )


def test_refuses_an_unsolved_atlas(tmp_path: Path) -> None:
    atlas = _tiny_atlas(tmp_path / "atlas.db")
    con = sqlite3.connect(atlas)
    with con:
        con.execute("UPDATE states SET value = NULL WHERE id = ?", (V,))
    con.close()
    with pytest.raises(ValueError, match="not solved"):
        build(atlas, tmp_path / "flags.db")


def test_refuses_to_overwrite(flagged: Path) -> None:
    with pytest.raises(FileExistsError):
        build(flagged / "atlas.db", flagged / "flags.db")
