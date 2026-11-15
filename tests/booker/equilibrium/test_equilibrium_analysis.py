"""Equilibrium pass on a hand-built solved atlas whose analysis can be read off by hand.

Root R (GTV 1; the state ids are STATE_ID_ROOT, STATE_ID_X, and so on) has four
Collider children (pairing: repeat cost, winners, GTV):
  C1 (0,1): cost 0, X=1 / Y=0, GTV 1  -> equilibrium, critical
  C2 (0,2): cost 1, Z=1 / Y=0, GTV 1  -> off: 1 + 1 > 1
  C3 (0,3): cost 0, W=2 / V=1, GTV 2  -> off: 0 + 2 > 1
  C4 (1,2): cost 0, X=1 / Z=1, GTV 1  -> equilibrium, indifferent
V is balanced off the equilibrium path: the Scheduler's C3 and the Collider's V cancel.
"""

from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from pathlib import Path

import pytest
from javhar_util.immutables import ZMap, ZVec

from booker.atlas.schema import open_connection
from booker.cli import main
from booker.equilibrium.equilibrium_analysis import (
    EquilibriumAnalysis,
    analyze_equilibrium,
    layer_summaries,
)
from booker.equilibrium.layer_summary import LayerSummary

STATE_ID_ROOT, STATE_ID_X, STATE_ID_Y, STATE_ID_Z, STATE_ID_W, STATE_ID_V = (
    1,
    2,
    3,
    4,
    5,
    6,
)
VALUES = ZMap(
    {
        STATE_ID_ROOT: 1,
        STATE_ID_X: 1,
        STATE_ID_Y: 0,
        STATE_ID_Z: 1,
        STATE_ID_W: 2,
        STATE_ID_V: 1,
    }
)


@dataclass(frozen=True)
class Collider:
    lhs: int
    rhs: int
    repeat_cost: int
    lhs_wins: int
    rhs_wins: int
    gtv: int


COLLIDERS = ZVec(
    [
        Collider(
            lhs=0,
            rhs=1,
            repeat_cost=0,
            lhs_wins=STATE_ID_X,
            rhs_wins=STATE_ID_Y,
            gtv=1,
        ),
        Collider(
            lhs=0,
            rhs=2,
            repeat_cost=1,
            lhs_wins=STATE_ID_Z,
            rhs_wins=STATE_ID_Y,
            gtv=1,
        ),
        Collider(
            lhs=0,
            rhs=3,
            repeat_cost=0,
            lhs_wins=STATE_ID_W,
            rhs_wins=STATE_ID_V,
            gtv=2,
        ),
        Collider(
            lhs=1,
            rhs=2,
            repeat_cost=0,
            lhs_wins=STATE_ID_X,
            rhs_wins=STATE_ID_Z,
            gtv=1,
        ),
    ]
)


@dataclass(frozen=True)
class SchedulerEquilibrium:
    equilibrium: bool
    fewest_past_repeats: int


def _tiny_atlas(path: Path) -> Path:
    connection = open_connection(path)
    with connection:
        connection.execute(
            "INSERT INTO meta VALUES ('root_id', ?)", (str(STATE_ID_ROOT),)
        )
        connection.execute("INSERT INTO meta VALUES ('solved', 'true')")
        for state_id, gtv in VALUES.items():
            depth = 0 if state_id == STATE_ID_ROOT else 1
            connection.execute(
                "INSERT INTO states (id, key, depth, active, expanded, gtv)"
                " VALUES (?, ?, ?, 2, 1, ?)",
                (state_id, bytes([state_id]), depth, gtv),
            )
        for collider in COLLIDERS:
            connection.execute(
                "INSERT INTO actions (parent, lhs, rhs, repeat_cost, class_size, lhs_wins,"
                " rhs_wins, gtv) VALUES (?, ?, ?, ?, 1, ?, ?, ?)",
                (
                    STATE_ID_ROOT,
                    collider.lhs,
                    collider.rhs,
                    collider.repeat_cost,
                    collider.lhs_wins,
                    collider.rhs_wins,
                    collider.gtv,
                ),
            )
    connection.close()
    return path


@pytest.fixture
def analyzed(tmp_path: Path) -> Path:
    atlas = _tiny_atlas(tmp_path / "atlas.db")
    analyze_equilibrium(atlas, tmp_path / "equilibrium.db")
    return tmp_path


def _query(analysis: Path, sql: str) -> list[tuple[int, ...]]:
    connection = sqlite3.connect(analysis)
    rows = connection.execute(sql).fetchall()
    connection.close()
    return rows


def test_scheduler_equilibrium(analyzed: Path) -> None:
    rows = _query(analyzed / "equilibrium.db", "SELECT * FROM scheduler_equilibrium")
    got = ZMap(
        {
            state_id: SchedulerEquilibrium(
                equilibrium=bool(equilibrium), fewest_past_repeats=past
            )
            for state_id, equilibrium, past in rows
        }
    )
    assert got == ZMap(
        {
            STATE_ID_ROOT: SchedulerEquilibrium(equilibrium=True, fewest_past_repeats=0),
            STATE_ID_X: SchedulerEquilibrium(equilibrium=True, fewest_past_repeats=0),
            STATE_ID_Y: SchedulerEquilibrium(equilibrium=False, fewest_past_repeats=0),
            STATE_ID_Z: SchedulerEquilibrium(equilibrium=True, fewest_past_repeats=0),
            STATE_ID_W: SchedulerEquilibrium(equilibrium=False, fewest_past_repeats=0),
            STATE_ID_V: SchedulerEquilibrium(equilibrium=False, fewest_past_repeats=0),
        }
    )


def test_collider_equilibrium(analyzed: Path) -> None:
    sql = "SELECT lhs, rhs, equilibrium, critical, fewest_past_repeats FROM collider_equilibrium"
    assert set(_query(analyzed / "equilibrium.db", sql)) == {
        (0, 1, 1, 1, 0),
        (0, 2, 0, 0, 1),
        (0, 3, 0, 0, 0),
        (1, 2, 1, 0, 0),
    }


def test_summary(analyzed: Path) -> None:
    layers = layer_summaries(analyzed / "atlas.db", analyzed / "equilibrium.db")
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


def _edit(atlas: Path, sql: str) -> Path:
    connection = sqlite3.connect(atlas)
    with connection:
        connection.execute(sql)
    connection.close()
    return atlas


def _only(directory: Path) -> list[str]:
    "The files in `directory`, but for the sidecars SQLite keeps beside a WAL database."
    return sorted(
        path.name
        for path in directory.iterdir()
        if not path.name.endswith(("-wal", "-shm"))
    )


@pytest.mark.parametrize(
    ("sql", "complaint"),
    [
        (
            f"UPDATE states SET gtv = NULL WHERE id = {STATE_ID_V}",
            "positions without a GTV",
        ),
        ("DELETE FROM meta WHERE key = 'solved'", "not been through"),
        ("PRAGMA user_version = 4", "schema v4"),
        ("PRAGMA user_version = 0", "schema v0"),
    ],
)
def test_refuses_an_atlas_it_cannot_read(
    tmp_path: Path, sql: str, complaint: str
) -> None:
    atlas = _edit(_tiny_atlas(tmp_path / "atlas.db"), sql)

    with pytest.raises(ValueError, match=complaint):
        analyze_equilibrium(atlas, tmp_path / "equilibrium.db")

    assert _only(tmp_path) == ["atlas.db"]


def test_an_unsolved_atlas_is_not_solved(tmp_path: Path) -> None:
    atlas = _edit(
        _tiny_atlas(tmp_path / "atlas.db"),
        f"UPDATE states SET gtv = NULL WHERE id = {STATE_ID_V}",
    )

    with pytest.raises(ValueError, match="not solved"):
        analyze_equilibrium(atlas, tmp_path / "equilibrium.db")


def test_refuses_to_overwrite(analyzed: Path) -> None:
    with pytest.raises(FileExistsError):
        analyze_equilibrium(analyzed / "atlas.db", analyzed / "equilibrium.db")


def test_a_failed_analysis_leaves_nothing_to_refuse_the_next(tmp_path: Path) -> None:
    atlas = _edit(
        _tiny_atlas(tmp_path / "atlas.db"),
        "INSERT INTO states (id, key, depth, active, expanded, gtv)"
        " VALUES (99, X'63', 1, 2, 1, 0)",
    )

    with pytest.raises(RuntimeError, match="never reached"):
        analyze_equilibrium(atlas, tmp_path / "equilibrium.db")

    assert _only(tmp_path) == ["atlas.db"]


def test_an_analysis_interrupted_in_the_middle_leaves_nothing_behind(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    analyze_depth = EquilibriumAnalysis._analyze_depth

    def analyze_then_fail(self: EquilibriumAnalysis, depth: int) -> None:
        analyze_depth(self, depth)
        raise KeyboardInterrupt

    monkeypatch.setattr(EquilibriumAnalysis, "_analyze_depth", analyze_then_fail)
    atlas = _tiny_atlas(tmp_path / "atlas.db")

    with pytest.raises(KeyboardInterrupt):
        analyze_equilibrium(atlas, tmp_path / "equilibrium.db")

    assert _only(tmp_path) == ["atlas.db"]


def test_a_stale_partial_analysis_is_replaced(tmp_path: Path) -> None:
    atlas = _tiny_atlas(tmp_path / "atlas.db")
    (tmp_path / "equilibrium.db.partial").write_text("left by a crash")

    analyze_equilibrium(atlas, tmp_path / "equilibrium.db")

    assert _only(tmp_path) == ["atlas.db", "equilibrium.db"]


def test_the_atlas_is_left_as_it_was(tmp_path: Path) -> None:
    atlas = _tiny_atlas(tmp_path / "atlas.db")
    before = hashlib.sha256(atlas.read_bytes()).hexdigest()

    analyze_equilibrium(atlas, tmp_path / "equilibrium.db")

    assert hashlib.sha256(atlas.read_bytes()).hexdigest() == before


def test_summarizing_an_analysis_that_does_not_exist_is_an_error(tmp_path: Path) -> None:
    atlas = _tiny_atlas(tmp_path / "atlas.db")

    with pytest.raises(FileNotFoundError):
        layer_summaries(atlas, tmp_path / "equilibrium.db")

    assert _only(tmp_path) == ["atlas.db"]


def test_the_command_analyzes_the_equilibrium_and_prints_each_depth(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    atlas = _tiny_atlas(tmp_path / "atlas.db")

    main(["equilibrium", str(atlas), str(tmp_path / "equilibrium.db")])

    lines = capsys.readouterr().out.splitlines()
    assert lines[0].split()[0] == "depth"
    assert [line.split() for line in lines[1:]] == [
        ["0", "1", "1", "0", "4", "2", "1"],
        ["1", "5", "2", "1", "0", "0", "0"],
    ]


def test_the_command_can_summarize_an_analysis_it_made_before(
    analyzed: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main(
        [
            "equilibrium",
            str(analyzed / "atlas.db"),
            str(analyzed / "equilibrium.db"),
            "--summary-only",
        ]
    )

    assert len(capsys.readouterr().out.splitlines()) == 3


def test_the_command_cannot_summarize_an_analysis_that_does_not_exist(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    atlas = _tiny_atlas(tmp_path / "atlas.db")

    with pytest.raises(SystemExit) as exit_info:
        main(["equilibrium", str(atlas), str(tmp_path / "none.db"), "--summary-only"])

    assert exit_info.value.code == 2
    assert "needs an analysis to summarize" in capsys.readouterr().err
    assert not (tmp_path / "none.db").exists()
