"""
Each implementation of `StateSymmetry` on cases whose answers are known, and all of them
against one another on states from games played at random, to every depth. They are
different algorithms on different libraries, so an answer on which they agree is not
a shared mistake.
"""

import itertools
import random
from collections import defaultdict
from collections.abc import Callable, Iterator, Mapping

import pytest
from support.pairings import pairing_of_indices
from support.states import state_of_indices

from booker.core.model.record import Record
from booker.core.model.state import State
from booker.core.symmetry.orbits import PairingOrbits
from booker.core.symmetry.relabelling import Relabelling
from booker.core.symmetry.state_signature import StateSignature
from booker.core.symmetry.state_symmetries import STATE_SYMMETRIES, VF2
from booker.core.symmetry.state_symmetry import StateSymmetry
from booker.game.rules import legal_pairings

IMPLEMENTATIONS = list(STATE_SYMMETRIES.values())
RECORD_1_1 = Record(wins=1, losses=1)
RECORD_1_0 = Record(wins=1, losses=0)
RECORD_0_1 = Record(wins=0, losses=1)
GAMES = 10
MOST_PAIRS_PER_GROUP = 15


def _relabelled(state: State, rng: random.Random) -> State:
    indices = list(range(state.size))
    rng.shuffle(indices)
    return Relabelling.of(indices).state(state)


def _pool(
    play_game: Callable[[random.Random], Iterator[State]],
) -> list[State]:
    rng = random.Random(0)
    return [state for _ in range(GAMES) for state in play_game(rng)]


@pytest.mark.parametrize("symmetry", IMPLEMENTATIONS)
def test_every_implementation_declares_that_it_implements_the_protocol(
    symmetry: StateSymmetry,
) -> None:
    assert StateSymmetry in type(symmetry).__mro__


@pytest.mark.parametrize("symmetry", IMPLEMENTATIONS)
def test_relabelled_states_are_isomorphic(symmetry: StateSymmetry) -> None:
    path = state_of_indices([RECORD_1_1] * 4, (0, 1), (1, 2), (2, 3))
    shuffled = state_of_indices([RECORD_1_1] * 4, (0, 2), (0, 3), (1, 3))

    assert symmetry.are_isomorphic(path, shuffled)


@pytest.mark.parametrize("symmetry", IMPLEMENTATIONS)
def test_a_path_is_not_a_star(symmetry: StateSymmetry) -> None:
    path = state_of_indices([RECORD_1_1] * 4, (0, 1), (1, 2), (2, 3))
    star = state_of_indices([RECORD_1_1] * 4, (0, 1), (0, 2), (0, 3))

    assert not symmetry.are_isomorphic(path, star)


@pytest.mark.parametrize("symmetry", IMPLEMENTATIONS)
def test_two_triangles_are_not_a_six_cycle(symmetry: StateSymmetry) -> None:
    "The same signature, so only the algorithm can tell them apart."
    triangles = state_of_indices(
        [RECORD_1_1] * 6, (0, 1), (1, 2), (0, 2), (3, 4), (4, 5), (3, 5)
    )
    cycle = state_of_indices(
        [RECORD_1_1] * 6, (0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (0, 5)
    )

    assert StateSignature.of(triangles) == StateSignature.of(cycle)
    assert not symmetry.are_isomorphic(triangles, cycle)


@pytest.mark.parametrize("symmetry", IMPLEMENTATIONS)
def test_records_must_match(symmetry: StateSymmetry) -> None:
    winner_at_the_end = state_of_indices(
        [RECORD_1_0, RECORD_0_1, RECORD_0_1], (0, 1), (1, 2)
    )
    winner_in_the_middle = state_of_indices(
        [RECORD_0_1, RECORD_1_0, RECORD_0_1], (0, 1), (1, 2)
    )

    assert not symmetry.are_isomorphic(winner_at_the_end, winner_in_the_middle)
    assert symmetry.are_isomorphic(
        winner_at_the_end,
        state_of_indices([RECORD_0_1, RECORD_0_1, RECORD_1_0], (0, 1), (1, 2)),
    )


@pytest.mark.parametrize("symmetry", IMPLEMENTATIONS)
def test_states_of_different_sizes_are_not_isomorphic(symmetry: StateSymmetry) -> None:
    assert not symmetry.are_isomorphic(
        state_of_indices([RECORD_1_1] * 2), state_of_indices([RECORD_1_1] * 3)
    )


@pytest.mark.parametrize("symmetry", IMPLEMENTATIONS)
def test_every_first_round_pairing_is_alike(symmetry: StateSymmetry) -> None:
    start = State.start()

    orbits = symmetry.orbits(start, legal_pairings(start))

    assert [(orbit.representative, orbit.size) for orbit in orbits] == [
        (pairing_of_indices(0, 1), 120)
    ]


@pytest.mark.parametrize("symmetry", IMPLEMENTATIONS)
def test_a_rematch_is_an_orbit_of_its_own(symmetry: StateSymmetry) -> None:
    state = state_of_indices([RECORD_1_1] * 4, (0, 1))

    orbits = symmetry.orbits(state, legal_pairings(state))

    assert [(orbit.representative, orbit.size) for orbit in orbits] == [
        (pairing_of_indices(0, 1), 1),
        (pairing_of_indices(0, 2), 4),
        (pairing_of_indices(2, 3), 1),
    ]


@pytest.mark.parametrize("symmetry", IMPLEMENTATIONS)
def test_a_decided_state_has_no_orbits(symmetry: StateSymmetry) -> None:
    decided = state_of_indices([Record(wins=6, losses=1)])

    assert len(symmetry.orbits(decided, legal_pairings(decided))) == 0


def _agree(answers: Mapping[str, object], what: object) -> None:
    first, *rest = answers.values()
    assert all(answer == first for answer in rest), (what, answers)


def test_every_implementation_finds_the_same_orbits(
    play_game: Callable[[random.Random], Iterator[State]],
) -> None:
    for state in _pool(play_game):
        pairings = legal_pairings(state)

        _agree(
            {
                symmetry.name: symmetry.orbits(state, pairings)
                for symmetry in IMPLEMENTATIONS
            },
            state,
        )


def test_every_implementation_knows_a_state_from_a_relabelling_of_it(
    play_game: Callable[[random.Random], Iterator[State]],
) -> None:
    rng = random.Random(1)

    for state in _pool(play_game):
        shuffled = _relabelled(state, rng)

        assert all(
            symmetry.are_isomorphic(state, shuffled) for symmetry in IMPLEMENTATIONS
        ), state


def _same_signature_pairs(states: list[State]) -> Iterator[tuple[State, State]]:
    groups: defaultdict[object, list[State]] = defaultdict(list)
    for state in states:
        groups[StateSignature.of(state)].append(state)
    for group in groups.values():
        yield from itertools.islice(
            itertools.combinations(group, 2), MOST_PAIRS_PER_GROUP
        )


def test_every_implementation_agrees_about_states_that_look_alike(
    play_game: Callable[[random.Random], Iterator[State]],
) -> None:
    verdicts: list[bool] = []

    for first, second in _same_signature_pairs(_pool(play_game)):
        answers = {
            symmetry.name: symmetry.are_isomorphic(first, second)
            for symmetry in IMPLEMENTATIONS
        }
        _agree(answers, (first, second))
        verdicts.append(answers["bliss"])

    assert True in verdicts
    assert False in verdicts


def test_orbits_are_a_partition_of_the_pairings(
    play_game: Callable[[random.Random], Iterator[State]],
) -> None:
    for state in _pool(play_game):
        pairings = legal_pairings(state)
        symmetry: StateSymmetry = VF2

        orbits: PairingOrbits = symmetry.orbits(state, pairings)

        assert orbits.pairings == pairings
