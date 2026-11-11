"""
The canonical relabelling of a schedule by BLISS: relabelled schedules are equal exactly
when they are isomorphic. Invariance is checked on random schedules, on states reached
by random results; distinctness on hand-built near misses.
"""

from __future__ import annotations

import random

import pytest
from javhar_util.immutables import ZSet, ZVec

from booker.core.model.outcome import Outcome
from booker.core.model.pairing import Pairing
from booker.core.model.record import Record
from booker.core.model.schedule import Schedule
from booker.core.model.state import State
from booker.core.model.successor import successor
from booker.core.model.team import Team
from booker.core.symmetry.bliss_graph import BlissGraph
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


def _canonical(schedule: Schedule) -> Schedule:
    return BlissGraph(schedule=schedule).canonical_relabelling.schedule(schedule)


def _schedule(
    *records: Record, past_pairings: tuple[Pairing, ...], pairings: tuple[Pairing, ...]
) -> Schedule:
    state = State(records=ZVec(records), past_pairings=ZSet(past_pairings))
    return Schedule(state=state, pairings=ZSet(pairings))


@pytest.mark.parametrize("seed", range(SAMPLES))
def test_invariant_under_relabelling(seed: int) -> None:
    rng = random.Random(seed)
    schedule = _random_schedule(rng)

    assert _canonical(_shuffled(schedule, rng)) == _canonical(schedule)


@pytest.mark.parametrize("seed", range(SAMPLES))
def test_a_canonical_schedule_is_its_own_canonical_schedule(seed: int) -> None:
    canonical = _canonical(_random_schedule(random.Random(seed)))

    assert _canonical(canonical) == canonical


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

    assert _canonical(path) != _canonical(star)


def test_distinguishes_records() -> None:
    past_pairings = (Pairing.of(TEAM_A, TEAM_B),)
    one = _schedule(
        RECORD_1_0, RECORD_0_1, RECORD_0_1, past_pairings=past_pairings, pairings=()
    )
    other = _schedule(
        RECORD_0_1, RECORD_1_0, RECORD_0_1, past_pairings=past_pairings, pairings=()
    )

    assert _canonical(one) == _canonical(other)
    assert _canonical(one) != _canonical(
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

    assert _canonical(rematches) != _canonical(fresh)
    assert _canonical(fresh) == _canonical(also_fresh)
