import pytest
from javhar_util.immutables import ZSet, ZVec
from support.pairings import pairing_of_indices

from booker.core.model.pairing import Pairing
from booker.core.model.team import Team
from booker.core.symmetry.orbits import PairingOrbit, PairingOrbits
from booker.verify.spot_check.action_row import ActionRow
from booker.verify.spot_check.audit_failure import AuditFailure
from booker.verify.spot_check.state_id import StateId


def test_builds_the_pairing_and_the_children_of_a_row() -> None:
    row = (2, 5, 1, 40, 41, 12, None)

    assert ActionRow.of(row) == ActionRow(
        pairing=Pairing.of(Team(index=2), Team(index=5)),
        repeat_cost=1,
        lhs_wins=StateId(value=40),
        rhs_wins=StateId(value=41),
        class_size=12,
        gtv=None,
    )


def test_a_solved_row_has_its_gtv() -> None:
    assert ActionRow.of((0, 1, 0, 2, 3, 1, 4)).gtv == 4


def test_the_columns_are_those_that_of_takes_in_order() -> None:
    assert ActionRow.COLUMNS.split(",") == [
        "lhs",
        "rhs",
        "repeat_cost",
        "lhs_wins",
        "rhs_wins",
        "class_size",
        "gtv",
    ]


PAIRING_01 = pairing_of_indices(0, 1)
PAIRING_02 = pairing_of_indices(0, 2)
PAIRING_03 = pairing_of_indices(0, 3)
TWO_ORBITS = PairingOrbits(
    orbits=ZVec(
        [
            PairingOrbit(members=ZSet([PAIRING_01, PAIRING_02])),
            PairingOrbit(members=ZSet([PAIRING_03])),
        ]
    )
)
STATE_ID = StateId(value=7)


def _rows(*sizes_by_rhs: tuple[int, int]) -> ZVec[ActionRow]:
    return ZVec(
        ActionRow.of((0, index_rhs, 0, 10, 11, class_size, None))
        for index_rhs, class_size in sizes_by_rhs
    )


def test_orbits_each_with_one_stored_pairing_of_their_size_are_accepted() -> None:
    ActionRow.require_orbits(STATE_ID, _rows((1, 2), (3, 1)), TWO_ORBITS)


def test_an_orbit_with_two_stored_pairings_fails_the_audit() -> None:
    with pytest.raises(AuditFailure, match="state 7: orbit representatives: 2 stored"):
        ActionRow.require_orbits(STATE_ID, _rows((1, 2), (2, 2), (3, 1)), TWO_ORBITS)


def test_an_orbit_with_no_stored_pairing_fails_the_audit() -> None:
    with pytest.raises(AuditFailure, match="orbit representatives: 0 stored"):
        ActionRow.require_orbits(STATE_ID, _rows((3, 1)), TWO_ORBITS)


def test_a_stored_pairing_of_the_wrong_size_fails_the_audit() -> None:
    with pytest.raises(AuditFailure, match="state 7: orbit sizes: .* is stored as 3"):
        ActionRow.require_orbits(STATE_ID, _rows((1, 3), (3, 1)), TWO_ORBITS)
