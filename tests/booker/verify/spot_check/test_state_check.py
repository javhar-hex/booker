"""
Each check of one position is shown to fire: a small, hand-built and fully solved atlas,
and the rest of a real game, are accepted, and then broken in one way at a time.
"""

from pathlib import Path

import pytest
from javhar_util.immutables import ZSet, ZVec
from support.hand_built_atlases import (
    PAIRING,
    RECORD_4_1,
    RECORD_5_1,
    RECORD_6_1,
    final_pair_atlas,
    hand_built_atlas,
    hand_built_state,
    tampered_copy,
)

from booker.core.model.pairing import Pairing
from booker.core.model.state import State
from booker.core.symmetry.bliss_symmetry import BlissSymmetry
from booker.core.symmetry.orbits import PairingOrbit, PairingOrbits
from booker.core.symmetry.state_symmetries import BLISS, VF2
from booker.core.symmetry.state_symmetry import StateSymmetry
from booker.verify.spot_check.atlas_reader import AtlasReader
from booker.verify.spot_check.audit_failure import AuditFailure
from booker.verify.spot_check.state_check import StateCheck
from booker.verify.spot_check.state_id import StateId
from booker.verify.spot_check.state_id_range import StateIdRange

ROOT, CHILD = 1, 2


def _check_every_state(
    atlas: Path,
    symmetry: StateSymmetry | None = None,
    first_id: int = 0,
    is_solved: bool = True,
) -> None:
    "Raises `AuditFailure` at the first position, from `first_id` on, that fails."
    with AtlasReader.open(str(atlas)) as db:
        check = StateCheck(db=db, symmetry=symmetry, is_solved=is_solved)
        for state_id in db.state_ids(StateIdRange.of(start=first_id)):
            check.run(state_id)


def test_accepts_a_solved_atlas(solved: Path) -> None:
    _check_every_state(solved)


def test_accepts_a_rematch_that_costs_one(tmp_path: Path) -> None:
    _check_every_state(final_pair_atlas(tmp_path / "rematch.db", met=True))


@pytest.mark.parametrize(
    ("sql", "first_id", "complaint"),
    [
        ("UPDATE states SET gtv=5 WHERE id=1", 0, "best action is worth"),
        ("UPDATE actions SET gtv=3", 0, "Collider GTV"),
        ("UPDATE actions SET repeat_cost=1", 0, "wrong repeat cost"),
        ("UPDATE actions SET lhs_wins=1", 0, "one match deeper"),
        ("UPDATE actions SET lhs_wins=99", 0, "does not exist"),
        ("UPDATE states SET expanded=0 WHERE id=1", 0, "unexpanded, with"),
        ("UPDATE states SET expanded=0 WHERE id=2", 0, "bad decided state"),
        ("UPDATE states SET gtv=1 WHERE id=2", CHILD, "worth 0"),
        ("UPDATE states SET depth=29 WHERE id=2", CHILD, "depth 29"),
        ("UPDATE states SET active=3 WHERE id=1", 0, "team count"),
        ("UPDATE states SET key=X'FF' WHERE id=2", CHILD, "invalid position"),
    ],
)
def test_rejects_a_solved_atlas_broken_in_one_way(
    solved: Path, sql: str, first_id: int, complaint: str
) -> None:
    with pytest.raises(AuditFailure, match=complaint):
        _check_every_state(tampered_copy(solved, sql), first_id=first_id)


@pytest.mark.parametrize(
    ("key", "depth", "complaint"),
    [
        ("020000 01", 28, "unbeaten teams cannot have met"),
        ("020D0200", 29, "a champion, with teams still playing"),
    ],
)
def test_rejects_an_impossible_position(
    solved: Path, key: str, depth: int, complaint: str
) -> None:
    sql = (
        "INSERT INTO states(key,depth,active,expanded,gtv) "
        f"VALUES (X'{key.replace(' ', '')}', {depth}, 2, 0, 0)"
    )

    with pytest.raises(AuditFailure, match=complaint):
        _check_every_state(tampered_copy(solved, sql), first_id=3)


def test_an_atlas_that_is_not_solved_is_not_held_to_its_gtvs(solved: Path) -> None:
    unsolved = tampered_copy(solved, "UPDATE states SET gtv=NULL WHERE id=1")

    _check_every_state(unsolved, is_solved=False)
    with pytest.raises(AuditFailure, match="unsolved"):
        _check_every_state(unsolved, is_solved=True)


def test_rejects_an_illegal_pairing(tmp_path: Path) -> None:
    atlas = hand_built_atlas(
        tmp_path / "illegal.db",
        hand_built_state(RECORD_5_1, RECORD_4_1),
        (hand_built_state(RECORD_6_1), hand_built_state(RECORD_5_1)),
        PAIRING,
    )

    with pytest.raises(AuditFailure, match="illegal pairings"):
        _check_every_state(atlas)


def test_rejects_a_dead_end(tmp_path: Path) -> None:
    atlas = hand_built_atlas(
        tmp_path / "dead.db",
        hand_built_state(RECORD_5_1, RECORD_4_1),
        (hand_built_state(RECORD_6_1), hand_built_state(RECORD_6_1)),
        pairing=None,
    )

    with pytest.raises(AuditFailure, match="dead end"):
        _check_every_state(atlas)


UNEQUAL_CHILDREN = (
    "SELECT action.rowid FROM actions action JOIN states x ON x.id = action.lhs_wins "
    "JOIN states y ON y.id = action.rhs_wins WHERE x.gtv != y.gtv LIMIT 1"
)
COLLIDER_AS_MIN = (
    "UPDATE actions SET gtv = (SELECT MIN(x.gtv, y.gtv) FROM states x, states y "
    f"WHERE x.id = actions.lhs_wins AND y.id = actions.rhs_wins) WHERE rowid = ({UNEQUAL_CHILDREN})"
)
ROOT_AS_MAX = (
    "UPDATE states SET gtv = (SELECT MAX(repeat_cost + gtv) FROM actions "
    f"WHERE parent = states.id) WHERE id = {ROOT}"
)
SWAPPED_CHILDREN = (
    "UPDATE actions SET lhs_wins = rhs_wins, rhs_wins = lhs_wins WHERE rowid = 1"
)
SWAPPED_SIZES = (
    f"UPDATE actions SET class_size = 3 - class_size WHERE parent = {ROOT} "
    "AND (lhs, rhs) IN ((0, 1), (0, 3))"
)


@pytest.mark.parametrize("symmetry", [None, BLISS, VF2])
def test_accepts_the_rest_of_a_real_game(
    endgame: Path, symmetry: StateSymmetry | None
) -> None:
    _check_every_state(endgame, symmetry=symmetry)


@pytest.mark.parametrize(
    ("sql", "complaint"),
    [
        (COLLIDER_AS_MIN, "Collider GTV"),
        (ROOT_AS_MAX, "best action is worth"),
        (f"UPDATE states SET gtv = gtv + 1 WHERE id = {ROOT}", "best action"),
        ("UPDATE actions SET gtv = gtv + 1 WHERE rowid = 1", "Collider GTV"),
    ],
)
def test_rejects_the_rest_of_a_real_game_wrong_gtv(
    endgame: Path, sql: str, complaint: str
) -> None:
    with pytest.raises(AuditFailure, match=complaint):
        _check_every_state(tampered_copy(endgame, sql))


class NeverIsomorphic(StateSymmetry):
    "Denies that any two states are alike, to show that the check asks."

    @property
    def name(self) -> str:
        return "never-isomorphic"

    def are_isomorphic(self, first: State, second: State) -> bool:
        return False

    def orbits(self, state: State, pairings: ZSet[Pairing]) -> PairingOrbits:
        return BlissSymmetry().orbits(state, pairings)


class SplitsEveryOrbit(StateSymmetry):
    "Finds every pairing alone in its orbit, to show that the check asks."

    @property
    def name(self) -> str:
        return "splits-every-orbit"

    def are_isomorphic(self, first: State, second: State) -> bool:
        return True

    def orbits(self, state: State, pairings: ZSet[Pairing]) -> PairingOrbits:
        return PairingOrbits(
            orbits=ZVec(
                PairingOrbit(members=ZSet([pairing])) for pairing in sorted(pairings)
            )
        )


def test_asks_the_symmetry_whether_children_are_the_right_ones(endgame: Path) -> None:
    with AtlasReader.open(str(endgame)) as db:
        StateCheck(db=db, symmetry=None, is_solved=True).run(StateId(value=ROOT))

        with pytest.raises(AuditFailure, match="wrong state"):
            StateCheck(db=db, symmetry=NeverIsomorphic(), is_solved=True).run(
                StateId(value=ROOT)
            )


def test_asks_the_symmetry_for_the_orbits(endgame: Path) -> None:
    with (
        AtlasReader.open(str(endgame)) as db,
        pytest.raises(AuditFailure, match="orbit (sizes|representatives)"),
    ):
        StateCheck(db=db, symmetry=SplitsEveryOrbit(), is_solved=True).run(
            StateId(value=ROOT)
        )


@pytest.mark.parametrize("symmetry", [None, BLISS, VF2])
def test_rejects_children_of_the_right_depth_that_are_swapped(
    endgame: Path, symmetry: StateSymmetry | None
) -> None:
    with pytest.raises(AuditFailure, match="wrong state"):
        _check_every_state(tampered_copy(endgame, SWAPPED_CHILDREN), symmetry=symmetry)


def test_only_a_symmetry_finds_orbit_sizes_that_add_up_but_are_swapped(
    endgame: Path,
) -> None:
    "One orbit of two pairings and one of a single pairing trade their sizes."
    tampered = tampered_copy(endgame, SWAPPED_SIZES)

    _check_every_state(tampered)
    for symmetry in (BLISS, VF2):
        with pytest.raises(AuditFailure, match="orbit sizes"):
            _check_every_state(tampered, symmetry=symmetry)
