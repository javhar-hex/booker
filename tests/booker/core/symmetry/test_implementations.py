"""
Each implementation of `Symmetry` on cases whose answers are known, and all of them
against one another on states from games played at random, to every depth. They are
different algorithms on different libraries, so an answer on which they agree is not
a shared mistake.
"""

import itertools
import random
from collections import defaultdict
from collections.abc import Callable, Iterator, Mapping

import pytest
from javhar_util.immutables import ZSet, ZVec

from booker.core.model.pairing import Pairing
from booker.core.model.record import Record
from booker.core.model.state import State
from booker.core.model.team import Team
from booker.core.symmetry.kinds import BLISS, VF2, SymmetryKind
from booker.core.symmetry.orbits import PairingOrbits
from booker.core.symmetry.relabelling import Relabelling
from booker.core.symmetry.symmetry import Symmetry, signature
from booker.game.rules import legal_pairings

KINDS = [BLISS, VF2]
ONE_ONE = Record(wins=1, losses=1)
WON = Record(wins=1, losses=0)
LOST = Record(wins=0, losses=1)
GAMES = 10
MOST_PAIRS_PER_GROUP = 15


def _pairing(a: int, b: int) -> Pairing:
    return Pairing.of(Team(index=a), Team(index=b))


def _state(records: list[Record], *met: tuple[int, int]) -> State:
    return State(records=ZVec(records), met=ZSet(_pairing(a, b) for a, b in met))


def _relabelled(state: State, rng: random.Random) -> State:
    indices = list(range(state.size))
    rng.shuffle(indices)
    return Relabelling.of(indices).state(state)


def _pool(
    play_game: Callable[[random.Random], Iterator[State]],
) -> list[State]:
    rng = random.Random(0)
    return [state for _ in range(GAMES) for state in play_game(rng)]


@pytest.mark.parametrize("kind", KINDS)
def test_relabelled_states_are_isomorphic(kind: SymmetryKind) -> None:
    path = _state([ONE_ONE] * 4, (0, 1), (1, 2), (2, 3))
    shuffled = _state([ONE_ONE] * 4, (0, 2), (0, 3), (1, 3))

    assert kind.symmetry.are_isomorphic(path, shuffled)


@pytest.mark.parametrize("kind", KINDS)
def test_a_path_is_not_a_star(kind: SymmetryKind) -> None:
    path = _state([ONE_ONE] * 4, (0, 1), (1, 2), (2, 3))
    star = _state([ONE_ONE] * 4, (0, 1), (0, 2), (0, 3))

    assert not kind.symmetry.are_isomorphic(path, star)


@pytest.mark.parametrize("kind", KINDS)
def test_two_triangles_are_not_a_six_cycle(kind: SymmetryKind) -> None:
    "The same signature, so only the algorithm can tell them apart."
    triangles = _state([ONE_ONE] * 6, (0, 1), (1, 2), (0, 2), (3, 4), (4, 5), (3, 5))
    cycle = _state([ONE_ONE] * 6, (0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (0, 5))

    assert signature(triangles) == signature(cycle)
    assert not kind.symmetry.are_isomorphic(triangles, cycle)


@pytest.mark.parametrize("kind", KINDS)
def test_records_must_match(kind: SymmetryKind) -> None:
    winner_at_the_end = _state([WON, LOST, LOST], (0, 1), (1, 2))
    winner_in_the_middle = _state([LOST, WON, LOST], (0, 1), (1, 2))

    assert not kind.symmetry.are_isomorphic(winner_at_the_end, winner_in_the_middle)
    assert kind.symmetry.are_isomorphic(
        winner_at_the_end, _state([LOST, LOST, WON], (0, 1), (1, 2))
    )


@pytest.mark.parametrize("kind", KINDS)
def test_states_of_different_sizes_are_not_isomorphic(kind: SymmetryKind) -> None:
    assert not kind.symmetry.are_isomorphic(_state([ONE_ONE] * 2), _state([ONE_ONE] * 3))


@pytest.mark.parametrize("kind", KINDS)
def test_every_first_round_pairing_is_alike(kind: SymmetryKind) -> None:
    start = State.start()

    orbits = kind.symmetry.orbits(start, legal_pairings(start))

    assert [(o.representative, o.size) for o in orbits] == [(_pairing(0, 1), 120)]


@pytest.mark.parametrize("kind", KINDS)
def test_a_rematch_is_an_orbit_of_its_own(kind: SymmetryKind) -> None:
    state = _state([ONE_ONE] * 4, (0, 1))

    orbits = kind.symmetry.orbits(state, legal_pairings(state))

    assert [(o.representative, o.size) for o in orbits] == [
        (_pairing(0, 1), 1),
        (_pairing(0, 2), 4),
        (_pairing(2, 3), 1),
    ]


@pytest.mark.parametrize("kind", KINDS)
def test_a_decided_state_has_no_orbits(kind: SymmetryKind) -> None:
    decided = _state([Record(wins=6, losses=1)])

    assert len(kind.symmetry.orbits(decided, legal_pairings(decided))) == 0


def _agree(answers: Mapping[str, object], what: object) -> None:
    first, *rest = answers.values()
    assert all(answer == first for answer in rest), (what, answers)


def test_every_implementation_finds_the_same_orbits(
    play_game: Callable[[random.Random], Iterator[State]],
) -> None:
    for state in _pool(play_game):
        pairings = legal_pairings(state)

        _agree({k.value: k.symmetry.orbits(state, pairings) for k in KINDS}, state)


def test_every_implementation_knows_a_state_from_a_relabelling_of_it(
    play_game: Callable[[random.Random], Iterator[State]],
) -> None:
    rng = random.Random(1)

    for state in _pool(play_game):
        shuffled = _relabelled(state, rng)

        assert all(k.symmetry.are_isomorphic(state, shuffled) for k in KINDS), state


def _same_signature_pairs(states: list[State]) -> Iterator[tuple[State, State]]:
    groups: defaultdict[object, list[State]] = defaultdict(list)
    for state in states:
        groups[signature(state)].append(state)
    for group in groups.values():
        yield from itertools.islice(
            itertools.combinations(group, 2), MOST_PAIRS_PER_GROUP
        )


def test_every_implementation_agrees_about_states_that_look_alike(
    play_game: Callable[[random.Random], Iterator[State]],
) -> None:
    verdicts: list[bool] = []

    for first, second in _same_signature_pairs(_pool(play_game)):
        answers = {k.value: k.symmetry.are_isomorphic(first, second) for k in KINDS}
        _agree(answers, (first, second))
        verdicts.append(answers["bliss"])

    assert True in verdicts
    assert False in verdicts


def test_orbits_are_a_partition_of_the_pairings(
    play_game: Callable[[random.Random], Iterator[State]],
) -> None:
    for state in _pool(play_game):
        pairings = legal_pairings(state)
        symmetry: Symmetry = VF2.symmetry

        orbits: PairingOrbits = symmetry.orbits(state, pairings)

        assert orbits.pairings == pairings
