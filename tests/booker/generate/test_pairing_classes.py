"""
Orbits of legal pairings under a state's automorphisms, on hand-countable states and
along random games. The closure of the rules under the symmetries is enforced by
the BLISS symmetry, which rejects additions that are not closed.
"""

import random
from collections.abc import Callable, Iterator

from javhar_util.immutables import ZSet, ZVec
from support.pairings import pairing_of_indices

from booker.core.model.pairing import Pairing
from booker.core.model.record import Record
from booker.core.model.state import State
from booker.core.symmetry.bliss_symmetry import BlissSymmetry
from booker.game.rules import legal_pairings

FRESH = Record(wins=0, losses=0)
ONE_ONE = Record(wins=1, losses=1)
WON = Record(wins=1, losses=0)
LOST = Record(wins=0, losses=1)


def _classes(state: State) -> list[tuple[Pairing, int]]:
    orbits = BlissSymmetry().orbits(state, legal_pairings(state))
    return [(orbit.representative, orbit.size) for orbit in orbits]


def _state(records: list[Record], past_pairings: list[Pairing]) -> State:
    return State(records=ZVec(records), past_pairings=ZSet(past_pairings))


def test_all_first_round_pairings_are_one_class() -> None:
    assert _classes(State.start()) == [(pairing_of_indices(0, 1), 120)]


def test_two_disjoint_matches_leave_three_classes() -> None:
    state = _state(
        [FRESH] * 12 + [WON, LOST, WON, LOST],
        [pairing_of_indices(12, 13), pairing_of_indices(14, 15)],
    )

    assert _classes(state) == [
        (pairing_of_indices(0, 1), 66),
        (pairing_of_indices(12, 14), 1),
        (pairing_of_indices(13, 15), 1),
    ]


def test_rematch_is_its_own_class() -> None:
    state = _state([ONE_ONE] * 4, [pairing_of_indices(0, 1)])

    assert _classes(state) == [
        (pairing_of_indices(0, 1), 1),
        (pairing_of_indices(0, 2), 4),
        (pairing_of_indices(2, 3), 1),
    ]


def test_decided_state_has_no_classes() -> None:
    assert _classes(_state([Record(wins=6, losses=0)], [])) == []


def test_legal_pairings_are_partitioned_by_their_orbits_along_every_game(
    play_game: Callable[[random.Random], Iterator[State]],
) -> None:
    rng = random.Random(0)

    for state in (state for _ in range(20) for state in play_game(rng)):
        orbits = BlissSymmetry().orbits(state, legal_pairings(state))
        assert orbits.pairings == legal_pairings(state)
