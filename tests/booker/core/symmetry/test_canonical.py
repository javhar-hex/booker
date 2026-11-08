"""
Canonical schedules: equal exactly for isomorphic schedules. Invariance is checked on
random schedules, on states reached by random results; distinctness on hand-built near
misses.
"""

from __future__ import annotations

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
from booker.core.symmetry.canonical import CanonicalSchedule, canonical_state
from booker.core.symmetry.relabelling import Relabelling

SAMPLES = 200
MAX_MATCHES = 24
MAX_SCHEDULED = 3
# Pairing only equal records below this many wins keeps every team under 6 wins.
WIN_CEILING = 4
TEAM_A, TEAM_B, TEAM_C, TEAM_D = (Team(index=idx) for idx in range(4))
RECORD_1_0 = Record(wins=1, losses=0)
RECORD_0_1 = Record(wins=0, losses=1)


def _random_state(rng: random.Random) -> State:
    state = State.start()
    for _ in range(rng.randrange(MAX_MATCHES + 1)):
        pairings = [
            Pairing.of(team_lhs, team_rhs)
            for team_lhs in state.teams
            for team_rhs in state.teams
            if team_lhs < team_rhs
            and state.record(team_lhs) == state.record(team_rhs)
            and state.record(team_lhs).wins <= WIN_CEILING
        ]
        if not pairings:
            break
        pairing = rng.choice(pairings)
        winner = rng.choice([pairing.lhs, pairing.rhs])
        state = successor(state, Outcome.single(pairing, winner))
    return state


def _random_schedule(rng: random.Random) -> Schedule:
    state = _random_state(rng)
    pairings = [
        Pairing.of(team_lhs, team_rhs)
        for team_lhs in state.teams
        for team_rhs in state.teams
        if team_lhs < team_rhs
    ]
    chosen = rng.sample(pairings, min(len(pairings), rng.randrange(MAX_SCHEDULED + 1)))
    return Schedule(state=state, pairings=ZSet(chosen))


def _shuffled(schedule: Schedule, rng: random.Random) -> Schedule:
    indices = list(range(schedule.state.size))
    rng.shuffle(indices)
    return Relabelling.of(indices).schedule(schedule)


def _schedule(
    *records: Record, past_pairings: tuple[Pairing, ...], pairings: tuple[Pairing, ...]
) -> Schedule:
    state = State(records=ZVec(records), past_pairings=ZSet(past_pairings))
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
        RECORD_1_0,
        RECORD_0_1,
        RECORD_0_1,
        RECORD_0_1,
        past_pairings=(
            Pairing.of(TEAM_A, TEAM_B),
            Pairing.of(TEAM_B, TEAM_C),
            Pairing.of(TEAM_C, TEAM_D),
        ),
        pairings=(),
    )
    star = _schedule(
        RECORD_1_0,
        RECORD_0_1,
        RECORD_0_1,
        RECORD_0_1,
        past_pairings=(
            Pairing.of(TEAM_A, TEAM_B),
            Pairing.of(TEAM_A, TEAM_C),
            Pairing.of(TEAM_A, TEAM_D),
        ),
        pairings=(),
    )

    assert CanonicalSchedule.of(path) != CanonicalSchedule.of(star)


def test_distinguishes_records() -> None:
    past_pairings = (Pairing.of(TEAM_A, TEAM_B),)
    one = _schedule(
        RECORD_1_0, RECORD_0_1, RECORD_0_1, past_pairings=past_pairings, pairings=()
    )
    other = _schedule(
        RECORD_0_1, RECORD_1_0, RECORD_0_1, past_pairings=past_pairings, pairings=()
    )

    assert CanonicalSchedule.of(one) == CanonicalSchedule.of(other)
    assert CanonicalSchedule.of(one) != CanonicalSchedule.of(
        _schedule(
            RECORD_0_1, RECORD_0_1, RECORD_0_1, past_pairings=past_pairings, pairings=()
        )
    )


def test_distinguishes_who_is_paired_with_whom() -> None:
    past_pairings = (Pairing.of(TEAM_A, TEAM_B), Pairing.of(TEAM_C, TEAM_D))
    four = (RECORD_0_1,) * 4
    rematches = _schedule(
        *four,
        past_pairings=past_pairings,
        pairings=(Pairing.of(TEAM_A, TEAM_B), Pairing.of(TEAM_C, TEAM_D)),
    )
    fresh = _schedule(
        *four,
        past_pairings=past_pairings,
        pairings=(Pairing.of(TEAM_A, TEAM_C), Pairing.of(TEAM_B, TEAM_D)),
    )
    also_fresh = _schedule(
        *four,
        past_pairings=past_pairings,
        pairings=(Pairing.of(TEAM_A, TEAM_D), Pairing.of(TEAM_B, TEAM_C)),
    )

    assert CanonicalSchedule.of(rematches) != CanonicalSchedule.of(fresh)
    assert CanonicalSchedule.of(fresh) == CanonicalSchedule.of(also_fresh)


def _graph(state: State) -> nx.Graph[int]:
    graph: nx.Graph[int] = nx.Graph()
    graph.add_nodes_from(
        (team.index, {"record": state.record(team)}) for team in state.teams
    )
    graph.add_edges_from(
        (pairing.lhs.index, pairing.rhs.index) for pairing in state.past_pairings
    )
    return graph


def test_canonical_state_is_isomorphic_to_the_original_by_networkx(
    play_game: Callable[[random.Random], Iterator[State]],
) -> None:
    "An oracle independent of igraph/BLISS, which the canonical form is built on."
    rng = random.Random(0)
    same_record = nx.algorithms.isomorphism.categorical_node_match("record", None)

    for state in (state for _ in range(20) for state in play_game(rng)):
        canonical = canonical_state(state)
        assert nx.is_isomorphic(_graph(canonical), _graph(state), node_match=same_record)


def test_a_state_and_its_relabelling_have_the_same_canonical_state() -> None:
    rng = random.Random(5)

    for seed in range(SAMPLES):
        state = _random_state(random.Random(seed))
        shuffled = _shuffled(Schedule.empty(state), rng).state

        assert canonical_state(shuffled) == canonical_state(state)
        assert canonical_state(canonical_state(state)) == canonical_state(state)


def test_the_canonical_state_is_that_of_the_canonical_schedule() -> None:
    state = _random_state(random.Random(0))

    assert (
        canonical_state(state)
        == CanonicalSchedule.of(Schedule.empty(state)).schedule.state
    )
