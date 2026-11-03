"""
Canonical schedules: equal exactly for isomorphic schedules. Invariance is checked on
random schedules, on states reached by random results; distinctness on hand-built near
misses.
"""

import random
from collections.abc import Callable, Iterator

import networkx as nx
import pytest
from javhar_util.immutables import ZSet, ZVec

from booker.core.model.outcome import Outcome
from booker.core.model.pairing import Pairing
from booker.core.model.record import Record
from booker.core.model.schedule import Schedule
from booker.core.model.state import State
from booker.core.model.successor import successor
from booker.core.model.team import Team
from booker.core.symmetry.canonical import CanonicalSchedule
from booker.core.symmetry.relabelling import Relabelling

SAMPLES = 200
MAX_MATCHES = 24
MAX_SCHEDULED = 3
# Pairing only equal records below this many wins keeps every team under 6 wins.
WIN_CEILING = 4
A, B, C, D = (Team(index=i) for i in range(4))
WON = Record(wins=1, losses=0)
ONE_LOSS = Record(wins=0, losses=1)


def _random_state(rng: random.Random) -> State:
    state = State.start()
    for _ in range(rng.randrange(MAX_MATCHES + 1)):
        pairings = [
            Pairing.of(x, y)
            for x in state.teams
            for y in state.teams
            if x < y
            and state.record(x) == state.record(y)
            and state.record(x).wins <= WIN_CEILING
        ]
        if not pairings:
            break
        pairing = rng.choice(pairings)
        winner = rng.choice([pairing.low, pairing.high])
        state = successor(state, Outcome.single(pairing, winner))
    return state


def _random_schedule(rng: random.Random) -> Schedule:
    state = _random_state(rng)
    pairings = [Pairing.of(x, y) for x in state.teams for y in state.teams if x < y]
    chosen = rng.sample(pairings, min(len(pairings), rng.randrange(MAX_SCHEDULED + 1)))
    return Schedule(state=state, pairings=ZSet(chosen))


def _shuffled(schedule: Schedule, rng: random.Random) -> Schedule:
    indices = list(range(schedule.state.size))
    rng.shuffle(indices)
    return Relabelling.of(indices).schedule(schedule)


def _schedule(
    *records: Record, met: tuple[Pairing, ...], pairings: tuple[Pairing, ...]
) -> Schedule:
    state = State(records=ZVec(records), met=ZSet(met))
    return Schedule(state=state, pairings=ZSet(pairings))


@pytest.mark.parametrize("seed", range(SAMPLES))
def test_invariant_under_relabelling(seed: int) -> None:
    rng = random.Random(seed)
    schedule = _random_schedule(rng)

    assert CanonicalSchedule.of(_shuffled(schedule, rng)) == CanonicalSchedule.of(
        schedule
    )


@pytest.mark.parametrize("seed", range(SAMPLES))
def test_canonical_schedule_is_its_own_canonical_schedule(seed: int) -> None:
    canonical = CanonicalSchedule.of(_random_schedule(random.Random(seed)))

    assert CanonicalSchedule.of(canonical.schedule) == canonical


def test_distinguishes_a_path_from_a_star() -> None:
    path = _schedule(
        WON,
        ONE_LOSS,
        ONE_LOSS,
        ONE_LOSS,
        met=(Pairing.of(A, B), Pairing.of(B, C), Pairing.of(C, D)),
        pairings=(),
    )
    star = _schedule(
        WON,
        ONE_LOSS,
        ONE_LOSS,
        ONE_LOSS,
        met=(Pairing.of(A, B), Pairing.of(A, C), Pairing.of(A, D)),
        pairings=(),
    )

    assert CanonicalSchedule.of(path) != CanonicalSchedule.of(star)


def test_distinguishes_records() -> None:
    met = (Pairing.of(A, B),)
    one = _schedule(WON, ONE_LOSS, ONE_LOSS, met=met, pairings=())
    other = _schedule(ONE_LOSS, WON, ONE_LOSS, met=met, pairings=())

    assert CanonicalSchedule.of(one) == CanonicalSchedule.of(other)
    assert CanonicalSchedule.of(one) != CanonicalSchedule.of(
        _schedule(ONE_LOSS, ONE_LOSS, ONE_LOSS, met=met, pairings=())
    )


def test_distinguishes_who_is_paired_with_whom() -> None:
    met = (Pairing.of(A, B), Pairing.of(C, D))
    four = (ONE_LOSS,) * 4
    rematches = _schedule(*four, met=met, pairings=(Pairing.of(A, B), Pairing.of(C, D)))
    fresh = _schedule(*four, met=met, pairings=(Pairing.of(A, C), Pairing.of(B, D)))
    also_fresh = _schedule(*four, met=met, pairings=(Pairing.of(A, D), Pairing.of(B, C)))

    assert CanonicalSchedule.of(rematches) != CanonicalSchedule.of(fresh)
    assert CanonicalSchedule.of(fresh) == CanonicalSchedule.of(also_fresh)


def _graph(state: State) -> nx.Graph[int]:
    graph: nx.Graph[int] = nx.Graph()
    graph.add_nodes_from(
        (team.index, {"record": state.record(team)}) for team in state.teams
    )
    graph.add_edges_from((p.low.index, p.high.index) for p in state.met)
    return graph


def test_canonical_state_is_isomorphic_to_the_original_by_networkx(
    play_game: Callable[[random.Random], Iterator[State]],
) -> None:
    "An oracle independent of igraph/BLISS, which the canonical form is built on."
    rng = random.Random(0)
    same_record = nx.algorithms.isomorphism.categorical_node_match("record", None)

    for state in (state for _ in range(20) for state in play_game(rng)):
        canonical = CanonicalSchedule.of(Schedule.empty(state)).schedule.state
        assert nx.is_isomorphic(_graph(canonical), _graph(state), node_match=same_record)
