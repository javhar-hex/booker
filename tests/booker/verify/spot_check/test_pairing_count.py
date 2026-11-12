from javhar_util.immutables import ZVec

from booker.verify.spot_check.action_row import ActionRow
from booker.verify.spot_check.pairing_count import PairingCount


def _row(index_rhs: int, class_size: int) -> ActionRow:
    return ActionRow.of((0, index_rhs, 0, 1, 2, class_size, None))


def test_counts_the_orbits_and_the_pairings_that_they_stand_for() -> None:
    rows = ZVec([_row(1, 4), _row(2, 1), _row(3, 10)])

    assert PairingCount.of(rows) == PairingCount(orbits=3, pairings=15)


def test_a_position_without_actions_counts_nothing() -> None:
    assert PairingCount.of(ZVec([])) == PairingCount.none()
    assert PairingCount.none() == PairingCount(orbits=0, pairings=0)


def test_counts_add_up() -> None:
    total = PairingCount(orbits=1, pairings=120).plus(PairingCount(orbits=2, pairings=7))

    assert total == PairingCount(orbits=3, pairings=127)
