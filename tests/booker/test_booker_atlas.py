"""Per-depth counts of the generated atlas, which are independent of the labelling.

REFERENCE was produced by the BLISS generator. Depths 0-3 (states, pairings) and 0-2
(Collider states) were also counted by hand, depths 0-5 agree with VF2,
and the Collider-state counts are confirmed independently by the verifier.
"""

from __future__ import annotations

import shutil
import sqlite3
from dataclasses import dataclass
from pathlib import Path

import pytest
from javhar_util.immutables import ZVec

from booker.core.symmetry.state_symmetries import BLISS, VF2
from booker.core.symmetry.state_symmetry import StateSymmetry
from booker.generate.atlas_expander import expand_atlas
from booker.solve import solve
from booker.verify.audit import audit
from booker.verify.failure import AuditFailure
from booker.verify.plan import AuditPlan, AuditReport, IdRange

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


def _generate(directory: Path, max_depth: int, symmetry: StateSymmetry) -> Path:
    directory.mkdir(exist_ok=True)
    db = directory / f"{symmetry.name}-{max_depth}.db"
    expand_atlas(str(db), max_depth=max_depth, symmetry=symmetry)
    return db


def _expanded_layers(db: Path, max_depth: int) -> ZVec[LayerCounts]:
    con = sqlite3.connect(db)
    rows = con.execute(
        """
        SELECT s.depth, COUNT(DISTINCT s.id), COUNT(action.parent),
               COALESCE(SUM(action.class_size), 0),
               COALESCE(SUM(action.repeat_cost * action.class_size), 0)
        FROM states s LEFT JOIN actions action ON action.parent = s.id
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
    return _generate(tmp_path_factory.mktemp("shallow"), SHALLOW_DEPTH, BLISS)


@pytest.fixture(scope="module")
def deep_atlas(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return _generate(tmp_path_factory.mktemp("deep"), len(REFERENCE), BLISS)


def test_layers_until_some_match_is_necessarily_outside_round_one(
    tmp_path: Path,
) -> None:
    max_depth = FIRST_ROUND_MATCHES + 2
    db = _generate(tmp_path, max_depth, BLISS)
    assert _expanded_layers(db, max_depth) == _reference_below(max_depth)


def test_bliss_and_vf2_agree(shallow_atlas: Path, tmp_path: Path) -> None:
    vf2_atlas = _generate(tmp_path, SHALLOW_DEPTH, VF2)
    expected = _expanded_layers(shallow_atlas, SHALLOW_DEPTH)
    assert _expanded_layers(vf2_atlas, SHALLOW_DEPTH) == expected


def test_bliss_and_vf2_agree_past_the_depth_they_were_first_trusted_to(
    tmp_path: Path,
) -> None:
    depth = SHALLOW_DEPTH + 3
    bliss = _generate(tmp_path / "bliss", depth, BLISS)
    vf2 = _generate(tmp_path / "vf2", depth, VF2)

    assert _expanded_layers(vf2, depth) == _expanded_layers(bliss, depth)
    assert _expanded_layers(bliss, depth) == _reference_below(depth)


def test_solve_refuses_a_truncated_atlas(shallow_atlas: Path) -> None:
    with pytest.raises(RuntimeError, match="truncated"):
        solve(str(shallow_atlas))


def _audit(
    db: Path,
    ids: IdRange | None = None,
    limit: int | None = None,
    checkpoint: Path | None = None,
    strict: StateSymmetry | None = None,
) -> AuditReport:
    plan = AuditPlan(
        db=str(db),
        strict=strict,
        ids=IdRange() if ids is None else ids,
        limit=limit,
        checkpoint=None if checkpoint is None else str(checkpoint),
    )
    return audit(plan, log=lambda message: None)


def test_verifier_accepts_the_shallow_atlas(shallow_atlas: Path) -> None:
    _audit(shallow_atlas)


def test_verifier_accepts_the_shallow_atlas_in_two_ranges(shallow_atlas: Path) -> None:
    middle = 10
    _audit(shallow_atlas, ids=IdRange(stop=middle))
    _audit(shallow_atlas, ids=IdRange(start=middle))


WRONG_ROOT_CLASS_SIZE = (
    "UPDATE actions SET class_size = class_size + 1 WHERE parent = {root}"
)
SPLIT_ROOT_ORBIT = (
    "UPDATE actions SET class_size = class_size / 2 WHERE parent = {root};"
    "INSERT INTO actions (parent, lhs, rhs, repeat_cost, class_size, lhs_wins, rhs_wins) "
    "SELECT parent, lhs, rhs + 1, repeat_cost, class_size, lhs_wins, rhs_wins "
    "FROM actions WHERE parent = {root};"
)
DUPLICATE_ROOT_REPRESENTATIVE = (
    "INSERT INTO actions (parent, lhs, rhs, repeat_cost, class_size, lhs_wins, rhs_wins) "
    "SELECT parent, lhs, rhs + 1, repeat_cost, class_size, lhs_wins, rhs_wins "
    "FROM actions WHERE parent = {root}"
)


def _root_id(db: Path) -> int:
    con = sqlite3.connect(db)
    (root,) = con.execute("SELECT value FROM meta WHERE key = 'root_id'").fetchone()
    con.close()
    return int(root)


def _tamper(db: Path, tampering: str) -> None:
    con = sqlite3.connect(db)
    con.executescript(tampering.format(root=_root_id(db)))
    con.close()


def _tampered(atlas: Path, directory: Path, tampering: str) -> Path:
    db = directory / "tampered.db"
    shutil.copy(atlas, db)
    _tamper(db, tampering)
    return db


@pytest.mark.parametrize("strict", [None, VF2])
@pytest.mark.parametrize(
    "tampering", [WRONG_ROOT_CLASS_SIZE, DUPLICATE_ROOT_REPRESENTATIVE]
)
def test_verifier_rejects_orbit_sizes_that_add_up_wrongly(
    shallow_atlas: Path, tmp_path: Path, tampering: str, strict: StateSymmetry | None
) -> None:
    db = _tampered(shallow_atlas, tmp_path, tampering)

    with pytest.raises(AuditFailure, match="orbit sizes add up"):
        _audit(db, strict=strict)


def test_only_the_strict_verifier_finds_two_stored_pairings_in_one_orbit(
    shallow_atlas: Path, tmp_path: Path
) -> None:
    "The sizes still add up to the number of legal pairings, but the orbit is split."
    db = _tampered(shallow_atlas, tmp_path, SPLIT_ROOT_ORBIT)

    _audit(db)
    with pytest.raises(AuditFailure, match="orbit representatives"):
        _audit(db, strict=VF2)


def test_verifier_range_checks_only_its_own_states(
    shallow_atlas: Path, tmp_path: Path
) -> None:
    db = _tampered(shallow_atlas, tmp_path, WRONG_ROOT_CLASS_SIZE)
    after_root = _root_id(db) + 1
    _audit(db, ids=IdRange(start=after_root))
    with pytest.raises(AuditFailure, match="orbit sizes add up"):
        _audit(db, ids=IdRange(stop=after_root))


@pytest.mark.slow
def test_layers_well_past_the_first_round(deep_atlas: Path) -> None:
    assert _expanded_layers(deep_atlas, len(REFERENCE)) == REFERENCE


@pytest.mark.slow
def test_verifier_accepts_the_deep_atlas(deep_atlas: Path) -> None:
    _audit(deep_atlas)


FIRST_SITTING = 5


def test_verifier_resumes_to_the_same_totals(
    shallow_atlas: Path, tmp_path: Path
) -> None:
    in_one_sitting = _audit(shallow_atlas)
    checkpoint = tmp_path / "progress.json"
    _audit(shallow_atlas, limit=FIRST_SITTING, checkpoint=checkpoint)

    assert _audit(shallow_atlas, checkpoint=checkpoint) == in_one_sitting


def test_verifier_resume_skips_states_already_checked(
    shallow_atlas: Path, tmp_path: Path
) -> None:
    db = tmp_path / "atlas.db"
    shutil.copy(shallow_atlas, db)
    checkpoint = tmp_path / "progress.json"
    _audit(db, limit=FIRST_SITTING, checkpoint=checkpoint)
    _tamper(db, WRONG_ROOT_CLASS_SIZE)
    _audit(db, checkpoint=checkpoint)


def test_verifier_refuses_a_checkpoint_from_another_range(
    shallow_atlas: Path, tmp_path: Path
) -> None:
    checkpoint = tmp_path / "progress.json"
    _audit(shallow_atlas, limit=FIRST_SITTING, checkpoint=checkpoint)
    with pytest.raises(AuditFailure, match="another run"):
        _audit(shallow_atlas, ids=IdRange(start=FIRST_SITTING), checkpoint=checkpoint)
