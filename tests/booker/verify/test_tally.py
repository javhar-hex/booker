from javhar_util.immutables import ZVec

from booker.verify.action_row import ActionRow
from booker.verify.tally import Tally


def _row(index_rhs: int, class_size: int) -> ActionRow:
    return ActionRow.of((0, index_rhs, 0, 1, 2, class_size, None))


def test_counts_the_actions_and_the_pairings_that_their_orbits_stand_for() -> None:
    rows = ZVec([_row(1, 4), _row(2, 1), _row(3, 10)])

    assert Tally.of(rows) == Tally(actions=3, pairings=15)


def test_a_position_without_actions_counts_nothing() -> None:
    assert Tally.of(ZVec([])) == Tally(actions=0, pairings=0)
