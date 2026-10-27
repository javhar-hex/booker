"""Per-depth counts of the generated atlas, which are independent of the labelling.

REFERENCE was produced by the BLISS generator. Depths 0-3 (states, pairings) and 0-2
(Collider states) were also counted by hand, depths 0-5 agree with the VF2 backend,
and the Collider-state counts are confirmed independently by the verifier.
"""

from __future__ import annotations

import shutil
import sqlite3
from dataclasses import dataclass
from pathlib import Path

import pytest
from javhar_util.immutables import ZVec

from booker.generate import generate, solve
from booker.verify import audit

FIRST_ROUND_MATCHES = 8
SHALLOW_DEPTH = 6


@dataclass(frozen=True)
class LayerCounts:
    depth: int
    states: int
    collider_states: int
    pairings: int
    rematch_pairings: int


REFERENCE = ZVec(
    LayerCounts(depth=d, states=s, collider_states=c, pairings=p, rematch_pairings=r)
    for d, s, c, p, r in [
        (0, 1, 1, 120, 0),
        (1, 1, 1, 91, 0),
        (2, 1, 3, 68, 0),
        (3, 3, 7, 185, 0),
        (4, 5, 15, 270, 1),
        (5, 11, 29, 513, 2),
        (6, 20, 63, 740, 2),
        (7, 35, 173, 1034, 7),
        (8, 98, 476, 2669, 20),
        (9, 227, 1179, 5264, 61),
        (10, 467, 2648, 9059, 132),
        (11, 946, 6285, 14955, 287),
    ]
)


def _generate(directory: Path, max_depth: int, backend: str) -> Path:
    db = directory / f"{backend}-{max_depth}.db"
    generate(str(db), max_depth=max_depth, backend=backend)
    return db


def _expanded_layers(db: Path, max_depth: int) -> ZVec[LayerCounts]:
    con = sqlite3.connect(db)
    rows = con.execute(
        """
        SELECT s.depth, COUNT(DISTINCT s.id), COUNT(a.parent),
               COALESCE(SUM(a.class_size), 0),
               COALESCE(SUM(a.repeat_cost * a.class_size), 0)
        FROM states s LEFT JOIN actions a ON a.parent = s.id
        WHERE s.depth < ? GROUP BY s.depth ORDER BY s.depth
        """,
        (max_depth,),
    ).fetchall()
    con.close()
    return ZVec(
        LayerCounts(depth=d, states=s, collider_states=c, pairings=p, rematch_pairings=r)
        for d, s, c, p, r in rows
    )


def _reference_below(max_depth: int) -> ZVec[LayerCounts]:
    return ZVec(layer for layer in REFERENCE if layer.depth < max_depth)


@pytest.fixture(scope="module")
def shallow_atlas(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return _generate(tmp_path_factory.mktemp("shallow"), SHALLOW_DEPTH, "bliss")


@pytest.fixture(scope="module")
def deep_atlas(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return _generate(tmp_path_factory.mktemp("deep"), len(REFERENCE), "bliss")


def test_layers_until_some_match_is_necessarily_outside_round_one(
    tmp_path: Path,
) -> None:
    max_depth = FIRST_ROUND_MATCHES + 2
    db = _generate(tmp_path, max_depth, "bliss")
    assert _expanded_layers(db, max_depth) == _reference_below(max_depth)


def test_bliss_and_vf2_backends_agree(shallow_atlas: Path, tmp_path: Path) -> None:
    vf2_atlas = _generate(tmp_path, SHALLOW_DEPTH, "vf2")
    expected = _expanded_layers(shallow_atlas, SHALLOW_DEPTH)
    assert _expanded_layers(vf2_atlas, SHALLOW_DEPTH) == expected


def test_solve_refuses_a_truncated_atlas(shallow_atlas: Path) -> None:
    with pytest.raises(RuntimeError, match="truncated"):
        solve(str(shallow_atlas))


def test_verifier_accepts_the_shallow_atlas(shallow_atlas: Path) -> None:
    audit(str(shallow_atlas))


def test_verifier_accepts_the_shallow_atlas_in_two_ranges(shallow_atlas: Path) -> None:
    middle = 10
    audit(str(shallow_atlas), to_id=middle)
    audit(str(shallow_atlas), from_id=middle)


WRONG_ROOT_CLASS_SIZE = (
    "UPDATE actions SET class_size = class_size + 1 WHERE parent = {root}"
)
DUPLICATE_ROOT_REPRESENTATIVE = (
    "INSERT INTO actions (parent, a, b, repeat_cost, class_size, a_wins, b_wins) "
    "SELECT parent, a, b + 1, repeat_cost, class_size, a_wins, b_wins "
    "FROM actions WHERE parent = {root}"
)


def _root_id(db: Path) -> int:
    con = sqlite3.connect(db)
    (root,) = con.execute("SELECT value FROM meta WHERE key = 'root_id'").fetchone()
    con.close()
    return int(root)


def _tamper(db: Path, tampering: str) -> None:
    con = sqlite3.connect(db)
    with con:
        con.execute(tampering.format(root=_root_id(db)))
    con.close()


def _tampered(atlas: Path, directory: Path, tampering: str) -> Path:
    db = directory / "tampered.db"
    shutil.copy(atlas, db)
    _tamper(db, tampering)
    return db


@pytest.mark.parametrize(
    "tampering, complaint",
    [
        (WRONG_ROOT_CLASS_SIZE, "sizes"),
        (DUPLICATE_ROOT_REPRESENTATIVE, "representatives"),
    ],
)
def test_verifier_rejects_wrong_pairing_classes(
    shallow_atlas: Path, tmp_path: Path, tampering: str, complaint: str
) -> None:
    db = _tampered(shallow_atlas, tmp_path, tampering)
    with pytest.raises(AssertionError, match=f"orbit {complaint}"):
        audit(str(db))


def test_verifier_range_checks_only_its_own_states(
    shallow_atlas: Path, tmp_path: Path
) -> None:
    db = _tampered(shallow_atlas, tmp_path, WRONG_ROOT_CLASS_SIZE)
    after_root = _root_id(db) + 1
    audit(str(db), from_id=after_root)
    with pytest.raises(AssertionError, match="orbit sizes"):
        audit(str(db), to_id=after_root)


@pytest.mark.slow
def test_layers_well_past_the_first_round(deep_atlas: Path) -> None:
    assert _expanded_layers(deep_atlas, len(REFERENCE)) == REFERENCE


@pytest.mark.slow
def test_verifier_accepts_the_deep_atlas(deep_atlas: Path) -> None:
    audit(str(deep_atlas))


FIRST_SITTING = 5


def _pass_line(captured: str) -> str:
    return next(line for line in captured.splitlines() if line.startswith("PASS"))


def test_verifier_resumes_to_the_same_totals(
    shallow_atlas: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    audit(str(shallow_atlas))
    in_one_sitting = _pass_line(capsys.readouterr().out)
    checkpoint = str(tmp_path / "progress.json")
    audit(str(shallow_atlas), limit=FIRST_SITTING, checkpoint=checkpoint)
    capsys.readouterr()
    audit(str(shallow_atlas), checkpoint=checkpoint)
    assert _pass_line(capsys.readouterr().out) == in_one_sitting


def test_verifier_resume_skips_states_already_checked(
    shallow_atlas: Path, tmp_path: Path
) -> None:
    db = tmp_path / "atlas.db"
    shutil.copy(shallow_atlas, db)
    checkpoint = str(tmp_path / "progress.json")
    audit(str(db), limit=FIRST_SITTING, checkpoint=checkpoint)
    _tamper(db, WRONG_ROOT_CLASS_SIZE)
    audit(str(db), checkpoint=checkpoint)


def test_verifier_refuses_a_checkpoint_from_another_range(
    shallow_atlas: Path, tmp_path: Path
) -> None:
    checkpoint = str(tmp_path / "progress.json")
    audit(str(shallow_atlas), limit=FIRST_SITTING, checkpoint=checkpoint)
    with pytest.raises(AssertionError, match="another run"):
        audit(str(shallow_atlas), from_id=FIRST_SITTING, checkpoint=checkpoint)
